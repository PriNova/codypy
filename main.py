import asyncio
import os

from dotenv import load_dotenv

from codypy.client_info import AgentSpecs, Models
from codypy.cody_py import CodyAgent, CodyServer
from codypy.config import GREEN, RESET, YELLOW, debug_method_map

load_dotenv()
SRC_ACCESS_TOKEN = os.getenv("SRC_ACCESS_TOKEN")
BINARY_PATH = os.getenv("BINARY_PATH")


async def main():

    # debug_method_map: Dict[str, Any] = await get_debug_map()

    # Create a CodyServer instance and initialize it with the specified binary path and debugging mode.
    print(f"{YELLOW}--- Create Server Connection ---{RESET}")
    cody_server: CodyServer = await CodyServer.init(
        binary_path=BINARY_PATH, version="0.0.5b", use_tcp = True, is_debugging=False
    )

    # Create an AgentSpecs instance with the specified workspace root URI and extension configuration.
    agent_specs = AgentSpecs(
        workspaceRootUri="/home/prinova/CodeProjects/CodyAgentPy",
        extensionConfiguration={
            "accessToken": SRC_ACCESS_TOKEN,
            "codebase": "", #"/home/prinova/CodeProjects/codypy",  # github.com/sourcegraph/cody",
            "customConfiguration": {},
        },
    )

    # Initialize the CodyAgent with the specified agent_specs and debug_method_map.
    print(f"{YELLOW}--- Initialize Agent ---{RESET}")
    cody_agent: CodyAgent = await cody_server.initialize_agent(
        agent_specs=agent_specs, is_debugging=False
    )

    # Retrieve and print the available chat models
    """print(f"{YELLOW}--- Retrieve Chat Models ---{RESET}")
    models = await cody_agent.get_models(model_type='chat', is_debugging=False)
    print(models)"""

    # Create a new chat with the CodyAgent
    print(f"{YELLOW}--- Create new chat ---{RESET}")
    await cody_agent.new_chat(is_debugging=False)

    # Set the chat model to Claude3Haiku
    print(f"{YELLOW}--- Set Model ---{RESET}")
    await cody_agent.set_model(
        model=Models.Claude3Haiku,
        is_debugging=False,
    )

    # Send a message to the chat and print the response until the user enters '/quit'.
    print(f"{YELLOW}--- Send message (short) ---{RESET}")
    debug_method_map["webview/postMessage"] = False
    contextFiles = [
        {
            "type": "file",
            "uri" : {
                "fsPath": "/home/prinova/CodeProjects/CodyAgentPy/main.py",
                "path": "/home/prinova/CodeProjects/CodyAgentPy/main.py",
            }
        }
    ]

    while True:
        message: str = input(f"{GREEN}Human:{RESET} ")
        response = await cody_agent.chat(
            message=message,
            enhanced_context=True,   # Set to 'True' if you wish Cody to be codebase aware
            contextFiles=contextFiles,         # Set to the list of files you want to have context for. See the example above
            is_debugging=True,
        )
        if response == "":
            break
        print(response)

    debug_method_map["webview/postMessage"] = True

    # Cleanup the server and return None
    await cody_server.cleanup_server()
    return None


if __name__ == "__main__":
    asyncio.run(main())
