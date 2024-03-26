import asyncio
import os

from dotenv import load_dotenv

from cody_agent_py.client_info import ClientInfo
from cody_agent_py.cody_agent_py import (
    cleanup_server_connection,
    create_server_connection,
    new_chat_session,
    send_initialization_message,
    get_configs,
    submit_chat_message,
)

load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")


async def main():
    config = await get_configs()
    config.BINARY_PATH = "/home/prinova/CodeProjects/cody/agent/dist"
    config.IS_DEBUGGING = False
    (reader, writer, process) = await create_server_connection(config)

    # Initialize the agent
    print("--- Initialize Agent ---")
    client_info = ClientInfo(
        workspaceRootUri=config.WORKSPACE,
        extensionConfiguration={
            "accessToken": ACCESS_TOKEN,
            "codebase": "github.com/sourcegraph/cody",
        },
    )
    server_info = await send_initialization_message(
        reader, writer, process, client_info
    )

    if server_info.authenticated:
        print("--- Server is authenticated ---")
    else:
        print("--- Server is not authenticated ---")
        cleanup_server_connection(writer, process)
        return

    # create a new chat
    print("--- Create new chat ---")
    result_id = await new_chat_session(reader, writer, process)

    # submit a chat message
    print("--- Send message (short) ---")

    # Wait for input from user in the CLI terminal
    text: str = input("Enter message: ")
    await submit_chat_message(reader, writer, process, text, result_id)

    # second input to show if conversation works
    text: str = input("Enter message: ")
    await submit_chat_message(reader, writer, process, text, result_id)

    # clean up server connection
    print("--- Cleanup server connection ---")
    await cleanup_server_connection(writer, process)


if __name__ == "__main__":
    asyncio.run(main())
