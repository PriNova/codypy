import asyncio
import os
import sys
from asyncio.subprocess import Process

from cody_agent_py.client_info import ClientInfo

from .config import Configs
from .messaging import (
    _handle_server_respones,
    _hasResult,
    _send_jsonrpc_request,
    _show_last_message,
)
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
) -> ServerInfo | None:
    await _send_jsonrpc_request(
        writer, "initialize", client_info.model_dump(warnings=True)
    )
    async for response in _handle_server_respones(reader):
        if configs.IS_DEBUGGING:
            print(f"Response: \n\n{response}\n")
        if response and await _hasResult(response):
            server_info: ServerInfo = ServerInfo.model_validate(response["result"])
            if configs.IS_DEBUGGING:
                print(f"Server Info: {server_info}\n")
            return server_info
    return None


async def new_chat_session(reader, writer, configs) -> str | None:
    await _send_jsonrpc_request(writer, "chat/new", None)
    async for response in _handle_server_respones(reader):
        if response and await _hasResult(response):
            result_id = response["result"]
            if configs.IS_DEBUGGING:
                print(f"Result: \n\n{result_id}\n")
            return result_id
    return None


async def submit_chat_message(reader, writer, text, result_id, configs):
    chat_message_request = {
        "id": f"{result_id}",
        "message": {
            "command": "submit",
            "text": text,
            "submitType": "user",
        },
    }
    await _send_jsonrpc_request(writer, "chat/submitMessage", chat_message_request)
    async for response in _handle_server_respones(reader):
        if response and await _hasResult(response):
            if configs.IS_DEBUGGING:
                print(f"Result: \n\n{response}\n")
            await _show_last_message(response["result"], configs)


async def cleanup_server_connection(writer, process):
    await _send_jsonrpc_request(writer, "shutdown", None)
    if process.returncode is None:
        process.terminate()
    await process.wait()
