import asyncio
import os
from typing import Any, Dict

from dotenv import load_dotenv

from cody_agent_py.client_info import AgentSpecs, Models
from cody_agent_py.cody_agent_py import CodyAgent, CodyServer
from cody_agent_py.config import GREEN, RESET, YELLOW, get_debug_map

load_dotenv()
SG_ACCESS_TOKEN = os.getenv("SG_ACCESS_TOKEN")


async def main():

    debug_method_map: Dict[str, Any] = await get_debug_map()

    # Create a CodyServer instance and initialize it with the specified binary path and debugging mode.
    print(f"{YELLOW}--- Create Server Connection ---{RESET}")
    cody_server: CodyServer = await CodyServer.init(
        binary_path="/home/prinova/CodeProjects/cody/agent/dist", is_debugging=True
    )

    # Create an AgentSpecs instance with the specified workspace root URI and extension configuration.
    agent_specs = AgentSpecs(
        workspaceRootUri="/home/prinova/CodeProjects/CodyAgentPy",
        extensionConfiguration={
            "accessToken": SG_ACCESS_TOKEN,
            "codebase": "https://github.com/PriNova/CodyAgentPy",  # github.com/sourcegraph/cody",
            "customConfiguration": {},
        },
    )

    # Initialize the CodyAgent with the specified agent_specs and debug_method_map.
    print(f"{YELLOW}--- Initialize Agent ---{RESET}")
    cody_agent: CodyAgent = await cody_server.initialize_agent(
        agent_specs=agent_specs, debug_method_map=debug_method_map, is_debugging=True
    )

    # Retrieve and print the available chat models
    print(f"{YELLOW}--- Retrieve Chat Models ---{RESET}")
    models = await cody_agent.get_models(
        model_type="chat", debug_method_map=debug_method_map, is_debugging=True
    )
    print(models)

    # Create a new chat with the CodyAgent
    print(f"{YELLOW}--- Create new chat ---{RESET}")
    await cody_agent.new_chat(debug_method_map=debug_method_map, is_debugging=True)

    # Set the chat model to Claude3Haiku
    print(f"{YELLOW}--- Set Model ---{RESET}")
    await cody_agent.set_model(
        model=Models.Claude3Haiku,
        debug_method_map=debug_method_map,
        is_debugging=True,
    )

    # Send a message to the chat and print the response until the user enters '/quit'.
    print(f"{YELLOW}--- Send message (short) ---{RESET}")
    debug_method_map["webview/postMessage"] = False

    while True:
        message: str = input(f"{GREEN}Human:{RESET} ")
        response = await cody_agent.chat(
            message=message,
            enhanced_context=False,
            debug_method_map=debug_method_map,
            is_debugging=False,
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
