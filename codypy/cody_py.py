import asyncio
import os
import sys
from asyncio.subprocess import Process
from typing import Any, Literal, Self, Tuple

from codypy.client_info import AgentSpecs, Models

from .config import BLUE, RED, RESET, YELLOW, Configs, debug_method_map
from .messaging import _send_jsonrpc_request, _show_last_message, request_response
from .server_info import CodyAgentSpecs


class CodyServer:

    async def init(
        binary_path: str, use_tcp: bool = False, is_debugging: bool = False
    ) -> Self:
        cody_agent = CodyServer(binary_path, use_tcp, is_debugging)
        await cody_agent._create_server_connection()
        return cody_agent

    def __init__(self, binary_path: str, use_tcp: bool, is_debugging: bool) -> None:
        self.binary_path = binary_path
        self.use_tcp = use_tcp
        self.is_debugging = is_debugging
        self._process: Process | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def _create_server_connection(self):
        """
        Asynchronously creates a connection to the Cody server.
        If `binary_path` is an empty string, it prints an error message and exits the program.
        Sets the `CODY_AGENT_DEBUG_REMOTE` and `CODY_DEBUG` environment variables based on the `use_tcp` and `is_debugging` flags, respectively.
        Creates a subprocess to run the Cody agent, either by executing the `bin/agent` binary or running the `index.js` file specified by `binary_path`.
        Depending on the `use_tcp` flag, it either connects to the agent using stdio or opens a TCP connection to `localhost:3113`.
        If the TCP connection fails after 5 retries, it prints an error message and exits the program.
        Returns the reader and writer streams for the agent connection.
        """
        if self.binary_path == "":
            print(
                f"{RED}You need to specify the BINARY_PATH to an absolute path to the agent binary or to the index.js file. Exiting...{RESET}"
            )
            sys.exit(1)

        os.environ["CODY_AGENT_DEBUG_REMOTE"] = str(self.use_tcp).lower()
        os.environ["CODY_DEBUG"] = str(self.is_debugging).lower()

        self._process: Process = await asyncio.create_subprocess_exec(
            "bin/cody-agent" if self.binary_path else "node",
            "jsonrpc" if self.binary_path else f"{self.binary_path}/index.js",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env=os.environ,
        )

        self._reader = self._process.stdout
        self._writer = self._process.stdin

        if not self.use_tcp:
            if self.is_debugging:
                print(f"{YELLOW}--- stdio connection ---{RESET}")
            self._reader = self._process.stdout
            self._writer = self._process.stdin

        else:
            if self.is_debugging:
                print(f"{YELLOW}--- TCP connection ---{RESET}")
            retry: int = 0
            retry_attempts: int = 5
            while retry < retry_attempts:
                try:
                    (self._reader, self._writer) = await asyncio.open_connection(
                        "localhost", 3113
                    )
                    if self._reader is not None and self._writer is not None:
                        print(f"{YELLOW}Connected to server: localhost:3113{RESET}\n")
                        break

                    # return reader, writer, process
                except ConnectionRefusedError:
                    await asyncio.sleep(0.1)  # Retry after a short delay
                    retry += 1
            print(f"{RED}Could not connect to server. Exiting...{RESET}")
            sys.exit(1)

    async def initialize_agent(
        self,
        agent_specs: AgentSpecs,
        debug_method_map,
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

        async def callback(result):
            cody_agent_specs: CodyAgentSpecs = CodyAgentSpecs.model_validate(result)
            if is_debugging:
                print(f"Agent Info: {cody_agent_specs}\n")
                if cody_agent_specs.authenticated:
                    print(f"{YELLOW}--- Server is authenticated ---{RESET}")
                else:
                    print(f"{RED}--- Server is not authenticated ---{RESET}")
                    await self.cleanup_server(self)
                    return None
            return await CodyAgent.init(self)

        return await request_response(
            "initialize",
            agent_specs.model_dump(),
            debug_method_map,
            self._reader,
            self._writer,
            is_debugging,
            callback,
        )

    async def cleanup_server(self):
        """
        Cleans up the server connection by sending a "shutdown" request to the server and terminating the server process if it is still running.
        """
        await _send_jsonrpc_request(self._writer, "shutdown", None)
        if self._process.returncode is None:
            self._process.terminate()
        await self._process.wait()


class CodyAgent:
    def __init__(self, cody_client: CodyServer) -> None:
        self._cody_server = cody_client
        self.chat_id: str | None = None

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

        async def callback(result):
            self.chat_id = result

        await request_response(
            "chat/new",
            None,
            debug_method_map,
            self._cody_server._reader,
            self._cody_server._writer,
            is_debugging,
            callback,
        )

    async def get_models(
        self,
        model_type: Literal["chat", "edit"],
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

        async def callback(result):
            return result

        model = {"modelUsage": f"{model_type}"}
        return await request_response(
            "chat/models",
            model,
            debug_method_map,
            self._cody_server._reader,
            self._cody_server._writer,
            is_debugging,
            callback,
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

        async def callback(result):
            return result

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
            callback,
        )

    async def chat(
        self,
        message,
        enhanced_context: bool = True,
        debug_method_map=debug_method_map,
        is_debugging: bool = False,
    ) -> str:
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

        if message == "/quit":
            return ""

        chat_message_request = {
            "id": f"{self.chat_id}",
            "message": {
                "command": "submit",
                "text": message,
                "submitType": "user",
                "addEnhancedContext": enhanced_context,
            },
        }

        result = await request_response(
            "chat/submitMessage",
            chat_message_request,
            debug_method_map,
            self._cody_server._reader,
            self._cody_server._writer,
            is_debugging
        )
        (speaker, response) = await _show_last_message(result, is_debugging)
        if speaker == "" or response == "":
            print(f"{RED}--- Failed to submit chat message ---{RESET}")
            await self._cody_server.cleanup_server()
            return None

        output = f"{BLUE}{speaker.capitalize()}{RESET}: {response}\n"
        return output


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
