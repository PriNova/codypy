import asyncio
import os
import sys
from asyncio.subprocess import Process
from typing import Any, Literal, Self, Tuple

from cody_agent_py.client_info import AgentSpecs
from cody_agent_py.messaging import request_response

from .config import Configs
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
        if self.binary_path == "":
            print(
                "You need to specify the BINARY_PATH to an absolute path to the agent binary or to the index.js file. Exiting..."
            )
            sys.exit(1)

        os.environ["CODY_AGENT_DEBUG_REMOTE"] = str(self.use_tcp).lower()
        os.environ["CODY_DEBUG"] = str(self.is_debugging).lower()

        self._process: Process = await asyncio.create_subprocess_exec(
            "bin/agent" if self.binary_path else "node",
            "jsonrpc" if self.binary_path else f"{self.binary_path}/index.js",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env=os.environ,
        )

        self._reader = self._process.stdout
        self._writer = self._process.stdin

        if not self.use_tcp:
            print("--- stdio connection ---")
            self._reader = self._process.stdout
            self._writer = self._process.stdin

        else:
            print("--- TCP connection ---")
            retry: int = 0
            while retry < 10:
                try:
                    (self._reader, self._writer) = await asyncio.open_connection(
                        "localhost", 3113
                    )
                    if self._reader is not None and self._writer is not None:
                        print(f"Connected to server: localhost:3113\n")
                        break

                    # return reader, writer, process
                except ConnectionRefusedError:
                    await asyncio.sleep(0.1)  # Retry after a short delay
                    retry += 1
            print("Could not connect to server. Exiting...")
            sys.exit(1)

    async def initialize_agent(
        self,
        agent_specs: AgentSpecs,
        debug_method_map,
        is_debugging: bool = False,
    ) -> CodyAgentSpecs | None:
        async def callback(result):
            cody_agent_specs: CodyAgentSpecs = CodyAgentSpecs.model_validate(result)
            if is_debugging:
                print(f"Agent Info: {cody_agent_specs}\n")
            if cody_agent_specs.authenticated:
                print("--- Server is authenticated ---")
            else:
                print("--- Server is not authenticated ---")
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
        await _send_jsonrpc_request(self._writer, "shutdown", None)
        if self._process.returncode is None:
            self._process.terminate()
        await self._process.wait()


class CodyAgent:
    def __init__(self, cody_client: CodyServer) -> None:
        self._cody_client = cody_client
        self.chat_id: str | None = None

    async def init(cody_client: CodyServer):
        return CodyAgent(cody_client)

    async def new_chat(self, debug_method_map, is_debugging: bool = False):
        async def callback(result):
            self.chat_id = result
            return result

        await request_response(
            "chat/new",
            None,
            debug_method_map,
            self._cody_client._reader,
            self._cody_client._writer,
            is_debugging,
            callback,
        )

    async def get_models(
        self, model_type: str, debug_method_map, is_debugging: bool = False
    ) -> Any:
        async def callback(result):
            return result

        model = {"modelUsage": f"{model_type}"}
        return await request_response(
            "chat/models",
            model,
            debug_method_map,
            self._cody_client._reader,
            self._cody_client._writer,
            is_debugging,
            callback,
        )

    async def set_model(
        self, model: str, debug_method_map, is_debugging: bool = False
    ) -> Any:
        async def callback(result):
            return result

        command = {
            "id": f"{self.chat_id}",
            "message": {"command": "chatModel", "model": f"{model}"},
        }

        return await request_response(
            "webview/receiveMessage",
            command,
            debug_method_map,
            self._cody_client._reader,
            self._cody_client._writer,
            is_debugging,
            callback,
        )

    async def chat(
        self,
        message,
        enhanced_context: bool,
        debug_method_map,
        is_debugging: bool = False,
    ) -> Tuple[str, str]:

        if message == "/quit":
            await self._cody_client.cleanup_server()
            sys.exit(0)

        chat_message_request = {
            "id": f"{self.chat_id}",
            "message": {
                "command": "submit",
                "text": message,
                "submitType": "user",
                "addEnhancedContext": enhanced_context,
            },
        }

        async def callback(result) -> Tuple[str, str]:
            return await _show_last_message(result, is_debugging)

        return await request_response(
            "chat/submitMessage",
            chat_message_request,
            debug_method_map,
            self._cody_client._reader,
            self._cody_client._writer,
            is_debugging,
            callback,
        )


async def get_remote_repositories(
    reader, writer, id: str, configs: Configs, debug_method_map
) -> Any:
    async def callback(result):
        return result

    return await request_response(
        "chat/remoteRepos", id, debug_method_map, reader, writer, configs, callback
    )


async def receive_webviewmessage(
    reader, writer, params, configs: Configs, debug_method_map
) -> Any:
    async def callback(result):
        return result

    return await request_response(
        "webview/receiveMessage",
        params,
        debug_method_map,
        reader,
        writer,
        configs,
        callback,
    )
