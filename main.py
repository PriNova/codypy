import asyncio
import os

from dotenv import load_dotenv

from cody_agent_py.client_info import ClientInfo
from cody_agent_py.cody_agent_py import (
    cleanup_server_connection,
    create_server_connection,
    get_models,
    new_chat_session,
    send_initialization_message,
    submit_chat_message,
)
from cody_agent_py.config import Configs, get_configs, get_debug_map
from cody_agent_py.server_info import ServerInfo

load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")


async def main():
    configs: Configs = await get_configs()
    configs.BINARY_PATH = "/home/prinova/CodeProjects/cody/agent/dist"
    configs.WORKSPACE = "/home/prinova/CodeProjects/codyTests"
    configs.IS_DEBUGGING = True

    debug_method_map = await get_debug_map()

    (reader, writer, process) = await create_server_connection(configs)
    if reader is None or writer is None:
        print("--- Failed to connect to server ---")
        cleanup_server_connection(writer, process)
        return None

    # Initialize the agent
    print("--- Initialize Agent ---")
    client_info = ClientInfo(
        workspaceRootUri=configs.WORKSPACE,
        extensionConfiguration={
            "accessToken": ACCESS_TOKEN,
            "codebase": "github.com/sourcegraph/cody",
        },
    )

    server_info: ServerInfo | None = await send_initialization_message(
        reader, writer, client_info, configs, debug_method_map
    )
    if server_info is None:
        print("--- Failed to initialize agent ---")
        await cleanup_server_connection(writer, process)
        return None

    if server_info.authenticated:
        print("--- Server is authenticated ---")
    else:
        print("--- Server is not authenticated ---")
        await cleanup_server_connection(writer, process)
        return None
    
    debug_method_map["webview/postMessage"] = False
    print("--- Retrieve Chat Models ---\n")     
    models = await get_models(reader, writer, 'edit', configs, debug_method_map)
    print(models)
    await cleanup_server_connection(writer, process)
    return None
    
    # create a new chat
    print("--- Create new chat ---")
    result_id: str = await new_chat_session(reader, writer, configs, debug_method_map)
    # result_id for restoring: 1d442f4f-d022-4d99-a1f5-8b8b7b26e3dc

    
    # submit a chat message
    print("--- Send message (short) ---")

    # set this to False otherwise your terminal will be full of streaming messages
    debug_method_map["webview/postMessage"] = False
    
    # Wait for input from user in the CLI terminal
    text: str = input("Enter message: ")
    (speaker, message) = await submit_chat_message(reader, writer, text, result_id, configs, debug_method_map)
    
    if speaker == "" or message == "":
        print("--- Failed to submit chat message ---")
        await cleanup_server_connection(writer, process)
        return None
    
    output = f"{speaker}: {message}\n"
    print(output)
    
    # second input to show if conversation works
    new_text: str = input("Enter message: ")
    (speaker, message) = await submit_chat_message(reader, writer, new_text, result_id, configs, debug_method_map)
    
    if speaker == "" or message == "":
        print("--- Failed to submit chat message ---")
        await cleanup_server_connection(writer, process)
        return None
    
    output = f"{speaker}: {message}\n"
    print(output)
    
    debug_method_map["webview/postMessage"] = True
    
    # clean up server connection
    print("--- Cleanup server connection ---")
    await cleanup_server_connection(writer, process)


if __name__ == "__main__":
    asyncio.run(main())
