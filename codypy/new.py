"""
Models around Cody agent
"""

import asyncio
import logging
import os
from asyncio.subprocess import Process
from datetime import datetime
from typing import Any, ForwardRef, Self

from codypy.client_info import AgentSpecs, Models

from .messaging import RPCClient
from .server_info import CodyAgentSpecs, Transcript

logger = logging.getLogger(__name__)


Chat = ForwardRef("Chat")


class CodyAgentClient(RPCClient):
    """Asynchronous I/O wrapper around Cody agent binary to make RPC calls

    :param cody_binary str: Path of the Cody agent binary
        To test against the cody agent source, you have set `cody_binary` as
        an empty string and set CODYPY_CODY_CMD environment variable with the
        full node command.
    :use_tcp bool: Enables agent communication via TCP socket via env var
                   CODY_AGENT_DEBUG_REMOTE. By default this is turned off
                   and communication is via process stdin/stdout.
    """

    def __init__(self, cody_binary: str, use_tcp: bool = False) -> None:
        super().__init__()
        self.cody_binary: str = cody_binary
        self.use_tcp = use_tcp
        self._process: Process | None = None
        self._binary_path: str
        self._binary_args: tuple[str, ...]
        self._binary_path, self._binary_args = self._prepare_binary()
        self.repos = {}

    @classmethod
    async def init(
        cls,
        binary_path: str,
        use_tcp: bool = False,
        agent_specs: AgentSpecs | None = None,
    ) -> Self:
        """Wrapper to asynchronously initialize the object

        This will also call create_process() (which is a blocking call)
        and initialize the session.
        """
        client = cls(cody_binary=binary_path, use_tcp=use_tcp)
        await client.create_process()
        if agent_specs:
            await client.initialize(agent_specs=agent_specs)
        return client

    def _prepare_binary(self) -> tuple[str, tuple[str, ...]]:
        """Find the right binary to use with the commands

        This function is mainly here to enable testability against
        Cody agent node source code directly instead of the binary

        In order to test against the compiled Cody agent source code,
        you can set CODYPY_CODY_CMD environment variable. Example:
        export CODYPY_CODY_CMD="node --enable-source-maps ~/CodeProjects/cody/agent/dist/index.js"
        """

        if custom_cmd := os.getenv("CODYPY_CODY_CMD"):
            logger.warning("Using custom cody command: %s", custom_cmd)
            tokens = custom_cmd.split(" ")
            return tokens[0], tuple(tokens[1:] + ["jsonrpc"])

        if not os.path.isfile(self.cody_binary):
            raise FileNotFoundError(
                "Cody binary at %s not found. Either fix the path "
                "or download the binary with `codypy download`"
            )
        return self.cody_binary, ("jsonrpc",)

    async def create_process(self) -> None:
        """Asynchronously creates a connection to the Cody server

        If the TCP connection is enabled, connection will be attempted 5 times
        before raising a ConnectionFailedError.
        """

        debug = logger.getEffectiveLevel() == logging.DEBUG
        self._process: Process = await asyncio.create_subprocess_exec(
            self._binary_path,
            *self._binary_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env={
                "CODY_AGENT_DEBUG_REMOTE": str(self.use_tcp).lower(),
                "CODY_DEBUG": str(debug).lower(),
            },
        )

        self.reader = self._process.stdout
        self.writer = self._process.stdin

        if self.use_tcp:
            logger.info("Initializing TCP connection to the Cody agent.")
            retry: int = 0
            retry_attempts: int = 5
            for retry in range(retry_attempts):
                try:
                    (self.reader, self.writer) = await asyncio.open_connection(
                        "localhost", 3113
                    )
                    if self.reader and self.writer:
                        logger.info("Connected to server: localhost:3113")
                        return
                except ConnectionRefusedError:
                    # Retry after a short delay
                    await asyncio.sleep(1)
                    retry += 1
            if retry == retry_attempts:
                raise ConnectionRefusedError(
                    f"Failed to connect to localhost:3113 after {retry} attempts."
                )
        else:
            logger.info("Created a stdio connection to the Cody agent.")

    async def initialize(self, agent_specs: AgentSpecs) -> None:
        """
        Initializes the Cody agent by sending an "initialize" request
        to the agent and handling the response.

        The method first creates a callback function that validates the
        response from the "initialize" request, prints the agent
        information if debugging is enabled, and checks if the server is
        authenticated.

        If the server is not authenticated, the method calls
        cleanup_server() and returns None.

        Finally, the method calls request_response to send the
        "initialize" request with the agent specifications, the debug
        method map, the reader and writer streams, the debugging flag,
        and the callback function.
        """

        response = await self.request_response("initialize", agent_specs.model_dump())
        cody_agent_specs: CodyAgentSpecs = CodyAgentSpecs.model_validate(response)
        logger.debug("Agent Info: %s", cody_agent_specs)
        if not cody_agent_specs.authenticated:
            logger.error("Server is not authenticated.")
            await self.cleanup_server()
            raise SystemError("Failed to authenticate to Cody agent")

        logger.info("Server is authenticated.")

    async def cleanup_server(self):
        """
        Cleans up the server connection by sending a "shutdown" request
        to the server and terminating the server process if it is still
        running.
        """
        logger.debug("Cleanup Server...")
        await self._send_jsonrpc_request("shutdown", None)
        if self._process.returncode is None:
            self._process.terminate()
        await self._process.wait()

    async def new_chat(self) -> Chat:
        """Initiates a new chat session with the Cody agent server."""
        new_chat_id = await self.request_response("chat/new", None)
        return Chat(chat_id=new_chat_id, client=self)

    async def restore_chat(self, messages: list[dict]) -> Chat:
        """Restore a conversation from an existing message stack"""
        new_chat_id = datetime.now().isoformat()
        params = {"messages": messages, "chatID": new_chat_id}
        await self.request_response("chat/restore", params)
        return Chat(chat_id=new_chat_id, client=self)

    async def _lookup_repo_ids(self, repos: list[str]) -> list[dict]:
        """Lookup repository objects via their names

        Results are cached in self.repos dictionary to avoid extra
        lookups if context is changed.

        Args:
            context_repos (list of strings):
                Name of the repositories which should be used for the
                chat context.

        Example:
        >>> client._lookup_repo_ids(["github.com/jsmith/awesomeapp"])
        [{"name":"github.com/jsmith/awesomeapp","id":"UmVwb3NpdG9yeToxMjM0"}]
        """

        if repos_to_lookup := [x for x in repos if x not in self.repos]:
            params = {"names": repos_to_lookup, "first": len(repos_to_lookup)}
            response = await self.request_response("graphql/getRepoIds", params)
            for repo in response["repos"]:
                self.repos[repo["name"]] = repo
            # If repo was not found, add it to the cache with a None
            # to avoid further lookups.
            for repo in repos:
                if repo not in self.repos:
                    self.repos[repo] = None

        return [self.repos[x] for x in repos if self.repos[x]]


class Chat:
    """Cody chat session"""

    def __init__(self, chat_id: str, client: CodyAgentClient) -> None:
        self.chat_id = chat_id
        self._client = client
        self.current_repo_context: list[str] = []

    async def set_context_repo(self, repos: list[str]) -> None:
        """Set repositories to use as context

        Args:
            context_repos (list of strings):
                Name of the repositories which should be used for the
                chat context.
        """

        if self.current_repo_context == repos:
            return

        self.current_repo_context = repos

        repo_objects = await self._client._lookup_repo_ids(repos=repos)

        # Configure the selected repositories for the chat context
        command = {
            "id": self.chat_id,
            "message": {
                "command": "context/choose-remote-search-repo",
                "explicitRepos": repo_objects,
            },
        }
        await self._client.request_response("webview/receiveMessage", command)

    async def get_models(self, model_type: str) -> Any:
        """Retrieves the available models for the specified model
        type (either "chat" or "edit") from the Cody agent server.

        Args:
            model_type (Literal["chat", "edit"]):
                The type of model to retrieve.

        Returns:
            Any: The result of the "chat/models" request.
        """

        model = {"modelUsage": model_type}
        return await self._client.request_response("chat/models", model)

    async def set_model(self, model: Models = Models.Claude3Sonnet) -> Any:
        """
        Sets the model to be used for the chat session.

        Args:
            model (Models): The model to be used for the chat session.
                            Defaults to Models.Claude3Sonnet.

        Returns:
            Any: The result of the "webview/receiveMessage" request.
        """

        command = {
            "id": f"{self.chat_id}",
            "message": {"command": "chatModel", "model": model.value.model_id},
        }

        return await self._client.request_response("webview/receiveMessage", command)

    async def ask(
        self,
        message,
        enhanced_context: bool = True,
        show_context_files: bool = False,
        context_files=None,
    ) -> Transcript:
        """Sends a chat message to the Cody server and returns the
        response.

        Args:
            message (str): The message to be sent to the Cody server.
            enhanced_context (bool, optional):
                Whether to include enhanced context in the chat message
                request. Defaults to True.

        Returns:
            str: The response from the Cody server, formatted as a
                 string with the speaker and response.
        """
        if context_files is None:
            context_files = []

        chat_req = {
            "id": self.chat_id,
            "message": {
                "command": "submit",
                "text": message,
                "submitType": "user",
                "addEnhancedContext": enhanced_context,
                "contextFiles": context_files,
            },
        }
        result = await self._client.request_response("chat/submitMessage", chat_req)
        return Transcript(**result)

    async def get_remote_repositories(self, repo_id: str) -> Any:
        return await self._client.request_response("chat/remoteRepos", repo_id)

    async def receive_webviewmessage(self, params: Any) -> Any:
        return await self._client.request_response("webview/receiveMessage", params)
