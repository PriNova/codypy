import asyncio
import os
import sys
from asyncio.subprocess import Process
from typing import Any, Self

from codypy.client_info import AgentSpecs, Models
from codypy.logger import log_message
from codypy.utils import (
    _check_for_binary_file,
    _download_binary_to_path,
    _format_binary_name,
)

from .config import BLUE, RED, RESET, YELLOW, Configs, debug_method_map
from .messaging import _send_jsonrpc_request, _show_last_message, request_response
from .server_info import CodyAgentSpecs


class CodyServer:
    async def init(
        binary_path: str,
        version: str,
        use_tcp: bool = False,  # default because of ca-certificate verification
        is_debugging: bool = False,
    ) -> Self:
        cody_binary = ""
        test_against_node_source: bool = (
            False  # Only for internal use to test against the Cody agent Node source
        )
        if not test_against_node_source:
            has_agent_binary = await _check_for_binary_file(
                binary_path, "cody-agent", version
            )
            if not has_agent_binary:
                log_message(
                    "CodyServer: init:",
                    f"WARNING: The Cody Agent binary does not exist at the specified path: {binary_path}",
                )
                print(
                    f"{YELLOW}WARNING: The Cody Agent binary does not exist at the specified path: {binary_path}{RESET}"
                )
                print(
                    f"{YELLOW}WARNING: Start downloading the Cody Agent binary...{RESET}"
                )
                is_completed = await _download_binary_to_path(
                    binary_path, "cody-agent", version
                )
                if not is_completed:
                    log_message(
                        "CodyServer: init:",
                        "ERROR: Failed to download the Cody Agent binary.",
                    )
                    print(
                        f"{RED}ERROR: Failed to download the Cody Agent binary.{RESET}"
                    )
                    sys.exit(1)

            cody_binary = os.path.join(
                binary_path, await _format_binary_name("cody-agent", version)
            )

        cody_agent = CodyServer(cody_binary, use_tcp, is_debugging)
        await cody_agent._create_server_connection(test_against_node_source)
        return cody_agent

    def __init__(self, cody_binary: str, use_tcp: bool, is_debugging: bool) -> None:
        self.cody_binary = cody_binary
        self.use_tcp = use_tcp
        self.is_debugging = is_debugging
        self._process: Process | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def _create_server_connection(
        self, test_against_node_source: bool = False
    ) -> None:
        """
        Asynchronously creates a connection to the Cody server.
        If `cody_binary` is an empty string, it prints an error message and exits the program.
        Sets the `CODY_AGENT_DEBUG_REMOTE` and `CODY_DEBUG` environment variables based on the `use_tcp` and `is_debugging` flags, respectively.
        Creates a subprocess to run the Cody agent, either by executing the `bin/agent` binary or running the `index.js` file specified by `binary_path`.
        Depending on the `use_tcp` flag, it either connects to the agent using stdio or opens a TCP connection to `localhost:3113`.
        If the TCP connection fails after 5 retries, it prints an error message and exits the program.
        Returns the reader and writer streams for the agent connection.
        """
        if not test_against_node_source and self.cody_binary == "":
            log_message(
                "CodyServer: _create_server_connection:",
                "ERROR: The Cody Agent binary path is empty.",
            )
            print(
                f"{RED}You need to specify the BINARY_PATH to an absolute path to the agent binary or to the index.js file. Exiting...{RESET}"
            )
            sys.exit(1)

        os.environ["CODY_AGENT_DEBUG_REMOTE"] = str(self.use_tcp).lower()
        os.environ["CODY_DEBUG"] = str(self.is_debugging).lower()

        args = []
        binary = ""
        if test_against_node_source:
            binary = "node"
            args.extend(
                (
                    "--enable-source-maps",
                    "/home/prinova/CodeProjects/cody/agent/dist/index.js",
                )
            )
        else:
            binary = self.cody_binary
        args.append("jsonrpc")
        self._process: Process = await asyncio.create_subprocess_exec(
            binary,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env=os.environ,
        )

        self._reader = self._process.stdout
        self._writer = self._process.stdin

        if not self.use_tcp:
            log_message(
                "CodyServer: _create_server_connection:",
                "Created a stdio connection to the Cody agent.",
            )
            if self.is_debugging:
                print(f"{YELLOW}--- stdio connection ---{RESET}")
            self._reader = self._process.stdout
            self._writer = self._process.stdin

        else:
            log_message(
                "CodyServer: _create_server_connection:",
                "Created a TCP connection to the Cody agent.",
            )
            if self.is_debugging:
                print(f"{YELLOW}--- TCP connection ---{RESET}")
            retry: int = 0
            retry_attempts: int = 5
            for retry in range(retry_attempts):
                try:
                    (self._reader, self._writer) = await asyncio.open_connection(
                        "localhost", 3113
                    )
                    if self._reader is not None and self._writer is not None:
                        log_message(
                            "CodyServer: _create_server_connection:",
                            "Connected to server: localhost:3113",
                        )
                        print(f"{YELLOW}Connected to server: localhost:3113{RESET}\n")
                        break

                    # return reader, writer, process
                except ConnectionRefusedError:
                    await asyncio.sleep(1)  # Retry after a short delay
                    retry += 1
            if retry == retry_attempts:
                log_message(
                    "CodyServer: _create_server_connection:",
                    "Could not connect to server. Exiting...",
                )
                print(f"{RED}Could not connect to server. Exiting...{RESET}")
                sys.exit(1)

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
        log_message(
            "CodyServer: initialize_agent:",
            f"Agent Info: {cody_agent_specs}",
        )
        if is_debugging:
            print(f"Agent Info: {cody_agent_specs}\n")
        if cody_agent_specs.authenticated:
            log_message(
                "CodyServer: initialize_agent:",
                "Server is authenticated.",
            )
            print(f"{YELLOW}--- Server is authenticated ---{RESET}")
        else:
            log_message(
                "CodyServer: initialize_agent:",
                "Server is not authenticated.",
            )
            print(f"{RED}--- Server is not authenticated ---{RESET}")
            await self.cleanup_server()
            sys.exit(1)
        return await CodyAgent.init(self)

    async def cleanup_server(self):
        """
        Cleans up the server connection by sending a "shutdown" request to the server and terminating the server process if it is still running.
        """
        log_message("CodyServer: cleanup_server:", "Cleanup Server...")
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

    async def init(cody_client: CodyServer):
        return CodyAgent(cody_client)

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
