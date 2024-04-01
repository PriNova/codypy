import asyncio
from json import JSONDecodeError
from typing import Any, AsyncGenerator, Dict, Tuple

import pydantic_core as pd

from cody_agent_py.config import Configs

message_id = 1


async def _send_jsonrpc_request(
    writer: asyncio.StreamWriter, method: str, params: Dict[str, Any] | None
) -> None:
    global message_id
    message: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": method,
        "params": params,
    }

    # Convert the message to JSON string
    json_message: str = pd.to_json(message).decode()
    content_length: int = len(json_message)
    content_message: str = f"Content-Length: {content_length}\r\n\r\n{json_message}"

    # Send the JSON-RPC message to the server
    writer.write(content_message.encode("utf-8"))
    await writer.drain()
    message_id += 1


async def _receive_jsonrpc_messages(reader: asyncio.StreamReader) -> str:
    headers: bytes = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5.0)
    content_length: int = int(
        headers.decode("utf-8").split("Content-Length:")[1].strip()
    )

    json_data: bytes = await asyncio.wait_for(
        reader.readexactly(content_length), timeout=5.0
    )
    return json_data.decode("utf-8")


async def _handle_server_respones(
    reader: asyncio.StreamReader,
) -> AsyncGenerator[Dict[str, Any], Any]:
    try:
        while True:
            response: str = await _receive_jsonrpc_messages(reader)
            yield pd.from_json(response)
    except asyncio.TimeoutError:
        yield pd.from_json("{}")


async def _hasMethod(json_response: Dict[str, Any]) -> bool:
    return "method" in json_response


async def _hasResult(json_response: Dict[str, Any]) -> bool:
    return "result" in json_response


async def _extraxtResult(json_response: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        return json_response["result"]
    except JSONDecodeError as e:
        return None


async def _extraxtMethod(json_response) -> Dict[str, Any] | None:
    try:
        return json_response["method"]
    except JSONDecodeError as e:
        return None


async def _handle_json_data(json_data, configs: Configs) -> Dict[str, Any] | None:
    json_response: Dict[str, Any] = pd.from_json(json_data)
    if await _hasMethod(json_response):
        if configs.IS_DEBUGGING:
            print(f"Method: {json_response['method']}\n")
        if "params" in json_response and configs.IS_DEBUGGING:
            print(f"Params: \n{json_response['params']}\n")
        return await _extraxtMethod(json_response)

    if await _hasResult(json_response):
        if configs.IS_DEBUGGING:
            print(f"Result: \n\n{await _extraxtResult(json_response)}\n")
        return await _extraxtResult(json_response)

    return json_response


async def _show_last_message(
    messages: Dict[str, Any], configs: Configs
) -> Tuple[str, str]:
    if messages["type"] == "transcript":
        last_message = messages["messages"][-1:]
        print(messages)
        if configs.IS_DEBUGGING:
            print(f"Last message: {last_message}")
        speaker: str = last_message[0]["speaker"]
        text: str = last_message[0]["text"]
        # output = f"{speaker}: {text}\n"
        return (speaker, text)
    return ("", "")


async def _show_messages(message, configs: Configs) -> None:
    if message["type"] == "transcript":
        for message in message["messages"]:
            if configs.IS_DEBUGGING:
                output = f"{message['speaker']}: {message['text']}\n"
                print(output)


async def request_response(
    method_name: str, params, debug_method_map, reader, writer, configs, callback=None
) -> Any:
    await _send_jsonrpc_request(writer, method_name, params)
    async for response in _handle_server_respones(reader):
        if configs.IS_DEBUGGING and await _hasMethod(response):
            method_name = response["method"]
            if method_name in debug_method_map and debug_method_map[method_name]:
                print(f"Response: \n\n{response}\n")
            if method_name not in debug_method_map:
                print(f"Response: \n\n{response}\n")

        if response and await _hasResult(response):
            if configs.IS_DEBUGGING:
                print(f"Result: \n\n{response}\n")
            if callback:
                return await callback(response["result"])

    return None
