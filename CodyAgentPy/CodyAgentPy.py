import asyncio
import json
import os

import pydantic_core as pd
import yaml
from dotenv import load_dotenv
from ServerInfo import ServerInfo

load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

# Load the YAML file
with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)

SERVER_ADDRESS = (
    config["CODY_AGENT_SERVER_HOST"],
    int(config["CODY_AGENT_SERVER_PORT"]),
)

WORKSPACE = config["ROOT_WORKSPACE"]

USE_BINARY = config['USE_BINARY']
BINARY_PATH = '' if USE_BINARY else config['BINARY_PATH']
USE_TCP = str(config["USE_TCP"]).lower()
os.environ["CODY_AGENT_DEBUG_REMOTE"] = USE_TCP

IS_DEBUG = False

message_id = 1

async def main():
    (reader, writer, process) = await create_server_connection(BINARY_PATH, USE_TCP)

    # Initialize the agent
    print ("--- Initialize Agent ---\n")
    await send_initialization_message(writer)
    server_info = None
    async for response in handle_server_respones(reader, process):
        if response and await hasResult(response):
            server_info: ServerInfo = ServerInfo.model_validate(response['result'])

    if server_info.authenticated:
        pass

    """# create a new chat
    print ("--- Create new chat ---\n")
    await send_jsonrpc_request(writer, 'chat/new', None)
    result_id = ''
    async for response in handle_server_respones(reader, process):
        if response and await hasResult(response):
            result_id = await extraxtResult(response)
            print(f"Result: \n\n{response}\n")

    # submit a chat message
    print("--- Send message (short) ---")
    chat_message_request = {
        "id": f'{result_id}',
        "message": {
            "command": "submit",
            "text": "How can I use docker in WSL2? Explain very briefly.",
            "submitType": "user",
        }
    }
    await send_jsonrpc_request(writer, 'chat/submitMessage', chat_message_request)
    async for response in handle_server_respones(reader, process):
        if response and await hasResult(response):
            print(f"Result: \n\n{response}\n")"""

    # clean up server connection
    await cleanup_server_connection(process)


async def create_server_connection(
    binary_path: str,
    use_tcp: str,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    process = await asyncio.create_subprocess_exec(
        "bin/agent" if USE_BINARY else "node",
        "jsonrpc" if USE_BINARY else f"{binary_path}/index.js",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        env=os.environ,
    )

    if use_tcp == "false":
        print("--- stdio connection ---\n")
        reader = process.stdout
        writer = process.stdin

    elif use_tcp == "true":
        print("--- TCP connection ---\n")
        while True:
            try:
                reader, writer = await asyncio.open_connection(*SERVER_ADDRESS)
                print(f"Connected to server: {SERVER_ADDRESS}\n")
                break
            except ConnectionRefusedError:
                await asyncio.sleep(0.1)  # Retry after a short delay

    return reader, writer, process

async def send_initialization_message(writer):
    (method, params) = await _initializing_message()
    await send_jsonrpc_request(writer, method, params)

async def _initializing_message():
    # Example JSON-RPC message
    method = "initialize"
    params = {
        "name": "defaultClient",
        "version": "v1",
        "workspaceRootUri": WORKSPACE,
        "workspaceRootPath": WORKSPACE,
        "extensionConfiguration": {
            "accessToken": ACCESS_TOKEN,
            "serverEndpoint": "https://sourcegraph.com",
            "codebase": "github.com/sourcegraph/cody",
        },
    }
    return method, params

async def send_jsonrpc_request(writer, method, params):
    global message_id
    # Create a JSON-RPC message
    message = {
        "jsonrpc": "2.0",
        "id": message_id,
        "method": method,
        "params": params,
    }

    # Convert the message to JSON string
    json_message = json.dumps(message)
    content_length = len(json_message)
    content_message = f"Content-Length: {content_length}\r\n\r\n{json_message}"

    # Send the JSON-RPC message to the server
    writer.write(content_message.encode('utf-8'))
    await writer.drain()
    message_id += 1

async def handle_server_respones(reader, process):
    try:
        while True:
            response = await receive_jsonrpc_messages(reader)
            """if not response:
                pass"""

            yield pd.from_json(response)
    except asyncio.TimeoutError:
        pass

async def receive_jsonrpc_messages(reader):
    headers = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), timeout=5.0)
    headers = headers.decode('utf-8')
    content_length = int(headers.split('Content-Length:')[1].strip())

    json_data = await asyncio.wait_for(reader.readexactly(content_length), timeout=5.0)
    return json_data.decode('utf-8')

async def _handle_json_data(json_data):
    json_response = pd.from_json(json_data)
    if await hasMethod(json_response):
        if IS_DEBUG: 
            print(f"Method: {json_response['method']}\n")
        if "params" in json_response and IS_DEBUG:
            print(f"Params: \n{json_response['params']}\n")
        return await extraxtMethod(json_response)

    if await hasResult(json_response):
        if  IS_DEBUG:
            print(f"Result: \n\n{await extraxtResult(json_response)}\n")
        return await extraxtResult(json_response)
            
    return json_response

async def cleanup_server_connection(process):
    if process.returncode is None:
        process.terminate()
    await process.wait()

async def hasMethod(json_response) -> bool:
    return "method" in json_response

async def hasResult(json_response)-> bool:
    return 'result' in json_response

async def extraxtResult(json_response) -> str:
    try:
        return json_response["result"]
    except json.JSONDecodeError as e:
        None

async def extraxtMethod(json_response) -> str:
    try:
        return json_response["method"]
    except json.JSONDecodeError as e:
        return None

if __name__ == "__main__":
    asyncio.run( main())