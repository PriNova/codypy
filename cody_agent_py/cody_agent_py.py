import asyncio
import os
import sys
from asyncio.subprocess import Process
from typing import Any, Tuple

from cody_agent_py.client_info import ClientInfo
from cody_agent_py.messaging import request_response

from .config import Configs
from .messaging import _send_jsonrpc_request, _show_last_message, request_response
from .server_info import ServerInfo


async def create_server_connection(
    configs: Configs,
) -> tuple[
    asyncio.StreamReader | None, asyncio.StreamWriter | None, asyncio.subprocess.Process
]:
    if configs.BINARY_PATH == "" or configs.BINARY_PATH is None:
        print(
            "You need to specify the BINARY_PATH to an absolute path to the agent binary or to the index.js file. Exiting..."
        )
        sys.exit(1)
    os.environ["CODY_AGENT_DEBUG_REMOTE"] = str(configs.USE_TCP).lower()
    os.environ["CODY_DEBUG"] = str(configs.IS_DEBUGGING).lower()
    process: Process = await asyncio.create_subprocess_exec(
        "bin/agent" if configs.USE_BINARY else "node",
        "jsonrpc" if configs.USE_BINARY else f"{configs.BINARY_PATH}/index.js",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        env=os.environ,
    )

    reader = process.stdout
    writer = process.stdin

    if not configs.USE_TCP:
        print("--- stdio connection ---")
        reader = process.stdout
        writer = process.stdin

    else:
        print("--- TCP connection ---")
        while True:
            try:
                (reader, writer) = await asyncio.open_connection(
                    *configs.SERVER_ADDRESS
                )
                print(f"Connected to server: {configs.SERVER_ADDRESS}\n")
                return reader, writer, process
            except ConnectionRefusedError:
                await asyncio.sleep(0.1)  # Retry after a short delay

    return reader, writer, process


async def send_initialization_message(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    client_info: ClientInfo,
    configs: Configs,
    debug_method_map,
) -> ServerInfo | None:
    async def callback(result):
        server_info: ServerInfo = ServerInfo.model_validate(result)
        if configs.IS_DEBUGGING:
            print(f"Server Info: {server_info}\n")
        return server_info

    return await request_response(
        "initialize",
        client_info.model_dump(),
        debug_method_map,
        reader,
        writer,
        configs,
        callback,
    )


async def new_chat_session(reader, writer, configs: Configs, debug_method_map) -> str:
    async def callback(result):
        return result

    return await request_response(
        "chat/new", None, debug_method_map, reader, writer, configs, callback
    )


async def submit_chat_message(
    reader, writer, text, id, configs: Configs, debug_method_map
) -> Tuple[str, str]:
    chat_message_request = {
        "id": f"{id}",
        "message": {
            "command": "submit",
            "text": text,
            "submitType": "user",
        },
    }

    async def callback(result) -> Tuple[str, str]:
        return await _show_last_message(result, configs)

    return await request_response(
        "chat/submitMessage",
        chat_message_request,
        debug_method_map,
        reader,
        writer,
        configs,
        callback,
    )


async def get_models(
    reader, writer, model_type, configs: Configs, debug_method_map
) -> Any:
    async def callback(result):
        return result

    model = {"modelUsage": f"{model_type}"}
    return await request_response(
        "chat/models", model, debug_method_map, reader, writer, configs, callback
    )


async def get_remote_repositories(
    reader, writer, id: str, configs: Configs, debug_method_map
) -> Any:
    async def callback(result):
        return result

    return await request_response(
        "chat/remoteRepos", id, debug_method_map, reader, writer, configs, callback
    )


async def set_model(
    reader, writer, id: str, model: str, configs: Configs, debug_method_map
) -> Any:
    async def callback(result):
        return result

    command = {"id": f"{id}", "message": {"command": "chatModel", "model": f"{model}"}}

    return await request_response(
        "webview/receiveMessage",
        command,
        debug_method_map,
        reader,
        writer,
        configs,
        callback,
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


async def cleanup_server_connection(writer, process):
    await _send_jsonrpc_request(writer, "shutdown", None)
    if process.returncode is None:
        process.terminate()
    await process.wait()
