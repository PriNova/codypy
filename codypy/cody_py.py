import asyncio
import logging
import os
import sys
from asyncio.subprocess import Process
from typing import Any

from codypy.client_info import AgentSpecs, Models

from .config import RED, RESET, YELLOW, Configs, debug_method_map
from .messaging import _send_jsonrpc_request, _show_last_message, request_response
from .server_info import CodyAgentSpecs

logger = logging.getLogger(__name__)


class CodyServer:
    """Asynchronous I/O wrapper around Cody agent binary

    :param cody_binary str: Path of the Cody agent binary
        To test against the cody agent source, you have set `cody_binary` as
        an empty string and set CODYPY_CODY_CMD environment variable with the
        full node command.
    :use_tcp bool: Enables agent communication via TCP socket via env var
                   CODY_AGENT_DEBUG_REMOTE. By default this is turned off
                   and communication is via process stdin/stdout.
    :param debug bool: Enables Cody agent debugging via env var CODY_DEBUG.
    """

    def __init__(
        self, cody_binary: str, use_tcp: bool = False, is_debugging: bool = False
    ) -> None:
        self.cody_binary: str = cody_binary
        self.use_tcp = use_tcp
        self.is_debugging = is_debugging
        self._process: Process | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._binary_path: str
        self._binary_args: tuple[str, ...]
        self._binary_path, self._binary_args = self._prepare_binary()

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

    async def connect(self) -> None:
        """Asynchronously creates a connection to the Cody server

        If the TCP connection is enabled, connection will be attempted 5 times
        before raising a ConnectionFailedError.
        """

        self._process: Process = await asyncio.create_subprocess_exec(
            self._binary_path,
            *self._binary_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env={
                "CODY_AGENT_DEBUG_REMOTE": str(self.use_tcp).lower(),
                "CODY_DEBUG": str(self.is_debugging).lower(),
            },
        )

        self._reader = self._process.stdout
        self._writer = self._process.stdin

        if self.use_tcp:
            logger.info("Initializing TCP connection to the Cody agent.")
            retry: int = 0
            retry_attempts: int = 5
            for retry in range(retry_attempts):
                try:
                    (self._reader, self._writer) = await asyncio.open_connection(
                        "localhost", 3113
                    )
                    if self._reader and self._writer:
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

    async def initialize_agent(
        self,
        agent_specs: AgentSpecs,
        debug_method_map=debug_method_map,
        is_debugging: bool = False,
    ) -> CodyAgentSpecs | None:
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

        response = await request_response(
            "initialize",
            agent_specs.model_dump(),
            debug_method_map,
            self._reader,
            self._writer,
            is_debugging,
        )

        cody_agent_specs: CodyAgentSpecs = CodyAgentSpecs.model_validate(response)
        logger.debug("Agent Info: %s", cody_agent_specs)
        if not cody_agent_specs.authenticated:
            logger.error("Server is not authenticated.")
            await self.cleanup_server()
            raise SystemError("Failed to authenticate to Cody agent")

        logger.info("Server is authenticated.")
        return CodyAgent(self)

    async def cleanup_server(self):
        """
        Cleans up the server connection by sending a "shutdown" request to the server and terminating the server process if it is still running.
        """
        logger.debug("Cleanup Server...")
        await _send_jsonrpc_request(self._writer, "shutdown", None)
        if self._process.returncode is None:
            self._process.terminate()
        await self._process.wait()


class CodyAgent:
    def __init__(self, cody_client: CodyServer) -> None:
        self._cody_server = cody_client
        self.chat_id: str | None = None
        self.repos: dict = {}
        self.current_repo_context: list[str] = []

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
            logger.error("Failed to submit chat message: %s", result)
            debug_method_map["webview/postMessage"] = True
            return f"{RED}--- Failed to submit chat message ---{RESET}"
        debug_method_map["webview/postMessage"] = True
        return (
            response,
            context_files_response,
        )


async def get_remote_repositories(
    reader, writer, id: str, configs: Configs, debug_method_map
) -> Any:
    return await request_response(
        "chat/remoteRepos", id, debug_method_map, reader, writer, configs
    )


async def receive_webviewmessage(
    reader, writer, params, configs: Configs, debug_method_map
) -> Any:
    return await request_response(
        "webview/receiveMessage",
        params,
        debug_method_map,
        reader,
        writer,
        configs,
    )
