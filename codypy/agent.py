import sys
from typing import Any

from codypy.client_info import AgentSpecs, Models
from codypy.config import RED, RESET, debug_method_map
from codypy.logger import log_message
from codypy.messaging import _show_last_message, request_response
from codypy.server import CodyServer
from codypy.server_info import CodyAgentInfo


class CodyAgent:
    def __init__(
        self,
        cody_server: CodyServer,
        agent_specs: AgentSpecs,
        debug_method_map=debug_method_map,
    ) -> None:
        self._cody_server = cody_server
        self.chat_id: str | None = None
        self.repos: dict = {}
        self.current_repo_context: list[str] = []
        self.agent_specs = agent_specs
        self.debug_method_map = debug_method_map

    async def initialize_agent(
        self,
        is_debugging: bool = False,
    ) -> None:
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
            cody_agent_specs: CodyAgentInfo = CodyAgentInfo.model_validate(response)
            log_message(
                "CodyServer: initialize_agent:",
                f"Agent Info: {cody_agent_specs}",
            )
            if is_debugging:
                print(f"Agent Info: {cody_agent_specs}\n")
            if not cody_agent_specs.authenticated:
                log_message(
                    "CodyServer: initialize_agent:",
                    "Server is not authenticated.",
                )
                print(f"{RED}--- Server is not authenticated ---{RESET}")
                await self.cleanup_server()
                sys.exit(1)

        response = await request_response(
            "initialize",
            self.agent_specs.model_dump(),
            debug_method_map,
            self._cody_server._reader,
            self._cody_server._writer,
            is_debugging,
        )

        await _handle_response(response)

    async def new_chat(
        self, debug_method_map=debug_method_map, is_debugging: bool = False
    ):
        """
        Initiates a new chat session with the Cody agent server.

        Args:
            debug_method_map (dict, optional): A mapping of debug methods to be used during the chat session.
            is_debugging (bool, optional): A flag indicating whether debugging is enabled. Defaults to False.
        """

        response = await request_response(
            "chat/new",
            None,
            debug_method_map,
            self._cody_server._reader,
            self._cody_server._writer,
            is_debugging,
        )

        self.chat_id = response

    async def _lookup_repo_ids(
        self,
        repos: list[str],
        debug_method_map=debug_method_map,
        is_debugging: bool = False,
    ) -> list[dict]:
        """Lookup repository objects via their names

        Results are cached in self.repos dictionary to avoid extra lookups
        if context is changed.

        Args:
            context_repos (list of strings): Name of the repositories which should
                                             be used for the chat context.
            debug_method_map (dict, optional): A mapping of debug methods to be
                                               used during the chat session.
            is_debugging (bool, optional): A flag indicating whether debugging is
                                           enabled. Defaults to False.
        """

        if repos_to_lookup := [x for x in repos if x not in self.repos]:
            # Example input: github.com/jsmith/awesomeapp
            # Example output: {"repos":[{"name":"github.com/jsmith/awesomeapp","id":"UmVwb3NpdG9yeToxMjM0"}]}
            response = await request_response(
                "graphql/getRepoIds",
                {"names": repos_to_lookup, "first": len(repos_to_lookup)},
                debug_method_map,
                self._cody_server._reader,
                self._cody_server._writer,
                is_debugging,
            )

            for repo in response["repos"]:
                self.repos[repo["name"]] = repo
            # Whatever we didn't find, add it to a cache with a None
            # to avoid further lookups.
            for repo in repos:
                if repo not in self.repos:
                    self.repos[repo] = None

        return [self.repos[x] for x in repos if self.repos[x]]

    async def set_context_repo(
        self,
        repos: list[str],
        debug_method_map=debug_method_map,
        is_debugging: bool = False,
    ) -> None:
        """Set repositories to use as context

        Args:
            context_repos (list of strings): Name of the repositories which should
                                             be used for the chat context.
            debug_method_map (dict, optional): A mapping of debug methods to be
                                               used during the chat session.
            is_debugging (bool, optional): A flag indicating whether debugging is
                                           enabled. Defaults to False.
        """

        if self.current_repo_context == repos:
            return

        self.current_repo_context = repos

        repo_objects = await self._lookup_repo_ids(
            repos=repos,
            debug_method_map=debug_method_map,
            is_debugging=is_debugging,
        )

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
            debug_method_map,
            self._cody_server._reader,
            self._cody_server._writer,
            is_debugging,
        )

    async def get_models(
        self,
        model_type: str,
        debug_method_map=debug_method_map,
        is_debugging: bool = False,
    ) -> Any:
        """
        Retrieves the available models for the specified model type (either "chat" or "edit") from the Cody agent server.

        Args:
            model_type (Literal["chat", "edit"]): The type of model to retrieve.
            debug_method_map (dict, optional): A mapping of debug methods to be used during the request. Defaults to `debug_method_map`.
            is_debugging (bool, optional): A flag indicating whether debugging is enabled. Defaults to False.

        Returns:
            Any: The result of the "chat/models" request.
        """

        model = {"modelUsage": f"{model_type}"}
        return await request_response(
            "chat/models",
            model,
            debug_method_map,
            self._cody_server._reader,
            self._cody_server._writer,
            is_debugging,
        )

    async def set_model(
        self,
        model: Models = Models.Claude3Sonnet,
        debug_method_map=debug_method_map,
        is_debugging: bool = False,
    ) -> Any:
        """
        Sets the model to be used for the chat session.

        Args:
            model (Models): The model to be used for the chat session. Defaults to Models.Claude3Sonnet.
            debug_method_map (dict, optional): A mapping of debug methods to be used during the request.
            is_debugging (bool, optional): A flag indicating whether debugging is enabled. Defaults to False.

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
            debug_method_map,
            self._cody_server._reader,
            self._cody_server._writer,
            is_debugging,
        )

    async def chat(
        self,
        message,
        enhanced_context: bool = True,
        show_context_files: bool = False,
        context_files=None,
        is_debugging: bool = False,
    ):
        """
        Sends a chat message to the Cody server and returns the response.

        Args:
            message (str): The message to be sent to the Cody server.
            enhanced_context (bool, optional): Whether to include enhanced context in the chat message request. Defaults to True.
            debug_method_map (dict, optional): A mapping of debug methods to be used during the request.
            is_debugging (bool, optional): A flag indicating whether debugging is enabled. Defaults to False.

        Returns:
            str: The response from the Cody server, formatted as a string with the speaker and response.
        """
        debug_method_map["webview/postMessage"] = False
        if context_files is None:
            context_files = []
        if message == "/quit":
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
            debug_method_map,
            self._cody_server._reader,
            self._cody_server._writer,
            is_debugging,
        )

        (speaker, response, context_files_response) = await _show_last_message(
            result, show_context_files, is_debugging
        )
        if speaker == "" or response == "":
            log_message(
                "CodyAgent: chat:",
                f"Failed to submit chat message: {result}",
            )
            debug_method_map["webview/postMessage"] = True
            return f"{RED}--- Failed to submit chat message ---{RESET}"
        debug_method_map["webview/postMessage"] = True
        return (
            response,
            context_files_response,
        )
