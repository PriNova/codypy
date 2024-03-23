import asyncio
import json
import os
import socket
import sys
from typing import Callable, Optional
import yaml

from dotenv import load_dotenv

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
BINARY_PATH = ''
if not USE_BINARY:
    BINARY_PATH = config['BINARY_PATH']

USE_TCP = str(config["USE_TCP"]).lower()
os.environ["CODY_AGENT_DEBUG_REMOTE"] = USE_TCP

message_id = 1

async def connect_to_server():
    (reader, writer, process) = await create_subprocess_connection(BINARY_PATH, USE_TCP)

    (method, params) = await initializing_message()

    # Send the JSON-RPC message to the server
    await send_jsonrpc_message(writer, method, params)

    try:
        while True:
            response = await receive_jsonrpc_messages(reader)
            if not response:
                break
            
            await process_json_data(response)
    finally:
        # Cleanup: terminate the process if it's still running
        if process.returncode is None:
            process.terminate()
        await process.wait()

async def create_subprocess_connection(
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
        print("Use stdio connection")
        reader = process.stdout
        writer = process.stdin

    elif use_tcp == "true":
        print("Use TCP connection")
        while True:
            try:
                reader, writer = await asyncio.open_connection(*SERVER_ADDRESS)
                print(f"Connected to server: {SERVER_ADDRESS}")
                break
            except ConnectionRefusedError:
                await asyncio.sleep(0.1)  # Retry after a short delay

    return reader, writer, process



async def initializing_message():
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

async def send_jsonrpc_message(writer, method, params):
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

async def receive_jsonrpc_messages(reader):
    while True:
        try:
            headers = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), timeout=5.0)
            headers = headers.decode('utf-8')
            content_length = int(headers.split('Content-Length:')[1].strip())

            json_data = await asyncio.wait_for(reader.readexactly(content_length), timeout=5.0)
            return json_data.decode('utf-8')
        
        except asyncio.TimeoutError:
            print('Timeout occurred while reading from the server')
            break

async def process_json_data(json_data):
    try:
        json_response = json.loads(json_data)
        if hasMethod(json_response):
            print(f"Method: {json_response['method']}")
            if "params" in json_response:
                print(f"Params: \n{json_response['params']}")
        if hasResult(json_response):
            print(f"Result: \n\n{extraxtResult(json_response)}")
    except Exception:
        pass

def hasMethod(json_response) -> bool:
    return "method" in json_response

def hasResult(json_response)-> bool:
    return 'result' in json_response

def extraxtResult(json_response) -> str:
    try:
        return json_response["result"]
    except json.JSONDecodeError as e:
        None

def extraxtMethod(json_response) -> str:
    try:
        return json_response["method"]
    except json.JSONDecodeError as e:
        return None

async def main():
    await connect_to_server()

if __name__ == "__main__":
    asyncio.run( main())