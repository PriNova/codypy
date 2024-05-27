import logging
from typing import Any

from codypy.client_info import AgentSpecs, Models
from codypy.exceptions import AgentAuthenticationError
from codypy.messaging import _show_last_message, request_response
from codypy.server import CodyServer
from codypy.server_info import CodyAgentInfo

logger = logging.getLogger(__name__)


class CodyAgent:
    def __init__(
        self,
        cody_server: CodyServer,
        agent_specs: AgentSpecs,
    ) -> None:
        self._cody_server = cody_server
        self.chat_id: str | None = None
        self.repos: dict = {}
        self.current_repo_context: list[str] = []
        self.agent_specs = agent_specs

    async def initialize_agent(self) -> None:
        """
        Initializes the Cody agent by sending an "initialize" request to the agent and handling the response.
        The method takes in agent specifications, a debug method map, and a boolean flag indicating whether debugging is enabled.
        It returns the initialized CodyAgentSpecs or None if the server is not authenticated.
        The method first creates a callback function that validates the response from the "initialize" request,
        prints the agent information if debugging is enabled, and checks if the server is authenticated.
        If the server is not authenticated, the method calls cleanup_server and returns None.
        Finally, the method calls request_response to send the "initialize" request with the agent specifications,
        the debug method map, the reader and writer streams, the debugging flag, and the callback function.
        """

        async def _handle_response(response: Any) -> None:
            # TODO: Consider attaching CodyAgentInfo to CodyAgent
            cody_agent_info: CodyAgentInfo = CodyAgentInfo.model_validate(response)
            # TODO: Prevent printing access token. Pydantic.SecretStr did not work
            logger.debug("CodyAgent initialized with specs: %s", self.agent_specs)
            logger.debug("CodyAgent Info: %s", cody_agent_info)
            if not cody_agent_info.authenticated:
                # TODO: Consider leaving the server process alive
                await self._cody_server.cleanup_server()
                raise AgentAuthenticationError("CodyAgent is not authenticated")
            logger.info("CodyAgent initialized successfully")

        response = await request_response(
            "initialize",
            self.agent_specs.model_dump(),
            self._cody_server._reader,
            self._cody_server._writer,
        )

        await _handle_response(response)

    async def new_chat(self):
        """Initiates a new chat session with the Cody agent server."""

        response = await request_response(
            "chat/new",
            None,
            self._cody_server._reader,
            self._cody_server._writer,
        )

        logger.info("New chat session %s created", response)
        self.chat_id = response

    async def _lookup_repo_ids(self, repos: list[str]) -> list[dict]:
        """Lookup repository objects via their names

        Results are cached in self.repos dictionary to avoid extra lookups
        if context is changed.

        Args:
            context_repos (list of strings): Name of the repositories which should
                                             be used for the chat context.
        """

        if repos_to_lookup := [x for x in repos if x not in self.repos]:
            # Example input: github.com/jsmith/awesomeapp
            # Example output: {"repos":[{"name":"github.com/jsmith/awesomeapp","id":"UmVwb3NpdG9yeToxMjM0"}]}
            response = await request_response(
                "graphql/getRepoIds",
                {"names": repos_to_lookup, "first": len(repos_to_lookup)},
                self._cody_server._reader,
                self._cody_server._writer,
            )

            for repo in response["repos"]:
                self.repos[repo["name"]] = repo
            # Whatever we didn't find, add it to a cache with a None
            # to avoid further lookups.
            for repo in repos:
                if repo not in self.repos:
                    self.repos[repo] = None

        return [self.repos[x] for x in repos if self.repos[x]]

    async def set_context_repo(self, repos: list[str]) -> None:
        """Set repositories to use as context

        Args:
            context_repos (list of strings): Name of the repositories which should
                                             be used for the chat context.
        """

        if self.current_repo_context == repos:
            return

        self.current_repo_context = repos

        repo_objects = await self._lookup_repo_ids(repos=repos)

        # Configure the selected repositories for the chat context
        command = {
            "id": self.chat_id,
            "message": {
                "command": "context/choose-remote-search-repo",
                "explicitRepos": repo_objects,
            },
        }
        await request_response(
            "webview/receiveMessage",
            command,
            self._cody_server._reader,
            self._cody_server._writer,
        )

    async def get_models(self, model_type: str) -> Any:
        """
        Retrieves the available models for the specified model type (either "chat" or "edit") from the Cody agent server.

        Args:
            model_type (Literal["chat", "edit"]): The type of model to retrieve.

        Returns:
            Any: The result of the "chat/models" request.
        """

        model = {"modelUsage": f"{model_type}"}
        return await request_response(
            "chat/models",
            model,
            self._cody_server._reader,
            self._cody_server._writer,
        )

    async def set_model(self, model: Models = Models.Claude3Sonnet) -> Any:
        """
        Sets the model to be used for the chat session.

        Args:
            model (Models): The model to be used for the chat session. Defaults to Models.Claude3Sonnet.

        Returns:
            Any: The result of the "webview/receiveMessage" request.
        """

        command = {
            "id": f"{self.chat_id}",
            "message": {"command": "chatModel", "model": f"{model.value.model_id}"},
        }

        return await request_response(
            "webview/receiveMessage",
            command,
            self._cody_server._reader,
            self._cody_server._writer,
        )

    async def chat(
        self,
        message,
        enhanced_context: bool = True,
        show_context_files: bool = False,
        context_files=None,
    ):
        """
        Sends a chat message to the Cody server and returns the response.

        Args:
            message (str): The message to be sent to the Cody server.
            enhanced_context (bool, optional): Whether to include enhanced context in the chat message request. Defaults to True.

        Returns:
            str: The response from the Cody server, formatted as a string with the speaker and response.
        """
        if context_files is None:
            context_files = []
        if message in ["/quit", "/bye", "/exit"]:
            return "", []

        chat_message_request = {
            "id": f"{self.chat_id}",
            "message": {
                "command": "submit",
                "text": message,
                "submitType": "user",
                "addEnhancedContext": enhanced_context,
                "contextFiles": context_files,
            },
        }

        result = await request_response(
            "chat/submitMessage",
            chat_message_request,
            self._cody_server._reader,
            self._cody_server._writer,
        )

        (speaker, response, context_files_response) = await _show_last_message(
            result,
            show_context_files,
        )
        if speaker == "" or response == "":
            logger.error("Failed to submit chat message: %s", result)
            return None
        return (response, context_files_response)
