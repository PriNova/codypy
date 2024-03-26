import asyncio
import json
import os
import sys

import pydantic_core as pd

from .config import Config
from .server_info import ServerInfo

config = Config("")

message_id = 1


async def get_configs():
    return config


async def create_server_connection(
    configs: Config,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    config = configs
    if config.BINARY_PATH == "" or config.BINARY_PATH is None:
        print(
            "You need to specify the BINARY_PATH to an absolute path to the agent binary or to the index.js file. Exiting..."
        )
        sys.exit(1)
    os.environ["CODY_AGENT_DEBUG_REMOTE"] = str(config.USE_TCP).lower()
    process = await asyncio.create_subprocess_exec(
        "bin/agent" if config.USE_BINARY else "node",
        "jsonrpc" if config.USE_BINARY else f"{config.BINARY_PATH}/index.js",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        env=os.environ,
    )

    reader = None
    writer = None

    if not config.USE_TCP:
        print("--- stdio connection ---")
        reader = process.stdout
        writer = process.stdin

    else:
        print("--- TCP connection ---")
        while True:
            try:
                reader, writer = await asyncio.open_connection(*config.SERVER_ADDRESS)
                print(f"Connected to server: {config.SERVER_ADDRESS}\n")
                break
            except ConnectionRefusedError:
                await asyncio.sleep(0.1)  # Retry after a short delay

    return reader, writer, process


async def send_initialization_message(
    reader, writer, process, client_info
) -> ServerInfo:

    await _send_jsonrpc_request(
        writer, "initialize", client_info.model_dump(warnings=True)
    )
    async for response in _handle_server_respones(reader, process):
        if config.IS_DEBUGGING:
            print(f"Response: \n\n{response}\n")
        if response and await _hasResult(response):
            server_info: ServerInfo = ServerInfo.model_validate(response["result"])
            if config.IS_DEBUGGING:
                print(f"Server Info: {server_info}\n")
            return server_info


async def new_chat_session(reader, writer, process) -> str:
    await _send_jsonrpc_request(writer, "chat/new", None)
    async for response in _handle_server_respones(reader, process):
        if response and await _hasResult(response):
            result_id = response["result"]
            if config.IS_DEBUGGING:
                print(f"Result: \n\n{result_id}\n")
            return result_id


async def submit_chat_message(reader, writer, process, text, result_id):
    chat_message_request = {
        "id": f"{result_id}",
        "message": {
            "command": "submit",
            "text": text,
            "submitType": "user",
        },
    }
    await _send_jsonrpc_request(writer, "chat/submitMessage", chat_message_request)
    async for response in _handle_server_respones(reader, process):
        if response and await _hasResult(response):
            if config.IS_DEBUGGING:
                print(f"Result: \n\n{response}\n")
            await _show_last_message(response["result"])


async def _show_last_message(messages):
    if messages["type"] == "transcript":
        last_message = messages["messages"][-1:]
        if config.IS_DEBUGGING:
            print(f"Last message: {last_message}")
        speaker = last_message[0]["speaker"]
        text = last_message[0]["text"]
        output = f"{speaker}: {text}\n"
        print(output)


async def _show_messages(message):
    if message["type"] == "transcript":
        for message in message["messages"]:
            if config.IS_DEBUGGING:
                output = f"{message['speaker']}: {message['text']}\n"
                print(output)


async def _send_jsonrpc_request(writer, method, params):
    global message_id
    message = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": method,
        "params": params,
    }

    # Convert the message to JSON string
    json_message: bytes = pd.to_json(message).decode()
    content_length: int = len(json_message)
    content_message = f"Content-Length: {content_length}\r\n\r\n{json_message}"

    # Send the JSON-RPC message to the server
    writer.write(content_message.encode("utf-8"))
    await writer.drain()
    message_id += 1


async def _handle_server_respones(reader, process):
    try:
        while True:
            response = await _receive_jsonrpc_messages(reader)
            yield pd.from_json(response)
    except asyncio.TimeoutError:
        pass


async def _receive_jsonrpc_messages(reader):
    headers = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5.0)
    headers = headers.decode("utf-8")
    content_length = int(headers.split("Content-Length:")[1].strip())

    json_data = await asyncio.wait_for(reader.readexactly(content_length), timeout=5.0)
    return json_data.decode("utf-8")


async def _handle_json_data(json_data):
    json_response = pd.from_json(json_data)
    if await _hasMethod(json_response):
        if config.IS_DEBUGGING:
            print(f"Method: {json_response['method']}\n")
        if "params" in json_response and config.IS_DEBUGGING:
            print(f"Params: \n{json_response['params']}\n")
        return await _extraxtMethod(json_response)

    if await _hasResult(json_response):
        if config.IS_DEBUGGING:
            print(f"Result: \n\n{await _extraxtResult(json_response)}\n")
        return await _extraxtResult(json_response)

    return json_response


async def cleanup_server_connection(writer, process):
    await _send_jsonrpc_request(writer, "exit", None)
    if process.returncode is None:
        process.terminate()
    await process.wait()


async def _hasMethod(json_response) -> bool:
    return "method" in json_response


async def _hasResult(json_response) -> bool:
    return "result" in json_response


async def _extraxtResult(json_response) -> str:
    try:
        return json_response["result"]
    except json.JSONDecodeError as e:
        None


async def _extraxtMethod(json_response) -> str:
    try:
        return json_response["method"]
    except json.JSONDecodeError as e:
        return None
