import asyncio

import pydantic_core as pd
from pydantic.json import JSONDecodeError

from cody_agent_py.cody_agent_py import config, message_id


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


async def _receive_jsonrpc_messages(reader):
    headers = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5.0)
    headers = headers.decode("utf-8")
    content_length = int(headers.split("Content-Length:")[1].strip())

    json_data = await asyncio.wait_for(reader.readexactly(content_length), timeout=5.0)
    return json_data.decode("utf-8")


async def _handle_server_respones(reader, process):
    try:
        while True:
            response = await _receive_jsonrpc_messages(reader)
            yield pd.from_json(response)
    except asyncio.TimeoutError:
        pass


async def _hasMethod(json_response) -> bool:
    return "method" in json_response


async def _hasResult(json_response) -> bool:
    return "result" in json_response


async def _extraxtResult(json_response) -> str:
    try:
        return json_response["result"]
    except JSONDecodeError as e:
        None


async def _extraxtMethod(json_response) -> str:
    try:
        return json_response["method"]
    except JSONDecodeError as e:
        return None


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
