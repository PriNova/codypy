import asyncio
import os

from dotenv import load_dotenv

from codypy.agent import CodyAgent
from codypy.client_info import AgentSpecs, Models
from codypy.config import BLUE, GREEN, RESET, YELLOW  # , debug_method_map
from codypy.context import append_paths
from codypy.logger import log_message, setup_logger
from codypy.server import CodyServer

load_dotenv()
SRC_ACCESS_TOKEN = os.getenv("SRC_ACCESS_TOKEN")
BINARY_PATH = os.getenv("BINARY_PATH")


async def main():
    # set the global logger
    setup_logger("codypy", "logs")

    # debug_method_map: Dict[str, Any] = await get_debug_map()

    # Create a CodyServer instance and initialize it
    # with the specified binary path and debugging mode.
    log_message("main:", "--- Create Server Connection ---")
    print(f"{YELLOW}--- Create Server Connection ---{RESET}")
    cody_server: CodyServer = await CodyServer.init(
        binary_path=BINARY_PATH, version="0.0.5b", is_debugging=False
    )

    # Create an AgentSpecs instance with the specified workspace root URI
    # and extension configuration.
    agent_specs = AgentSpecs(
        workspaceRootUri="/home/prinova/CodeProjects/CodyAgentPy",
        extensionConfiguration={
            "accessToken": SRC_ACCESS_TOKEN,
            "codebase": "",  # "/home/prinova/CodeProjects/codypy",  # github.com/sourcegraph/cody",
            "customConfiguration": {},
        },
    )

    # Initialize the CodyAgent with the specified agent_specs and debug_method_map.
    log_message("main:", "--- Initialize Agent ---")
    print(f"{YELLOW}--- Initialize Agent ---{RESET}")
    cody_agent: CodyAgent = CodyAgent(cody_server=cody_server, agent_specs=agent_specs)
    await cody_agent.initialize_agent(is_debugging=False)

    # Retrieve and print the available chat models
    log_message("main:", "--- Retrieve Chat Models ---")
    print(f"{YELLOW}--- Retrieve Chat Models ---{RESET}")
    models = await cody_agent.get_models(model_type="chat", is_debugging=False)
    print(models)
    # Create a new chat with the CodyAgent
    log_message("main:", "--- Create new chat ---")
    print(f"{YELLOW}--- Create new chat ---{RESET}")
    await cody_agent.new_chat(is_debugging=False)

    # Set the chat model to Claude3Haiku
    log_message("main:", "--- Set Model ---")
    print(f"{YELLOW}--- Set Model ---{RESET}")
    await cody_agent.set_model(
        model=Models.Claude3Sonnet,
        is_debugging=False,
    )

    # Set the repository context
    log_message("main:", "--- Set context repo ---")
    print(f"{YELLOW}--- Set context repo ---{RESET}")
    await cody_agent.set_context_repo(
        repos=["github.com/PriNova/codypy"],
        is_debugging=False,
    )

    # Send a message to the chat and print the response until the user enters '/quit'.
    log_message("main:", "--- Send message (short) ---")
    print(f"{YELLOW}--- Send message (short) ---{RESET}")

    # set specified context files to be used by Cody of your choice in the workspace
    context_file = append_paths(
        "/home/prinova/CodeProjects/CodyAgentPy/main.py",
        "/home/prinova/CodeProjects/CodyAgentPy/codypy/logger.py",
    )

    while True:
        message: str = input(f"{GREEN}Human:{RESET} ")
        response, context_files_response = await cody_agent.chat(
            message=message,
            # Set to 'True' if you wish Cody to be codebase aware
            enhanced_context=False,
            # Set to 'True' if the inferred context files with optional ranges
            # should be returned else an empty list
            show_context_files=True,
            # Set to the list of files you want to have context for. See the example above
            context_files=context_file,
            is_debugging=False,
        )
        if response == "":
            break
        print(f"{BLUE}Assistant{RESET}: {response}\n")
        print("--- Context Files ---")
        if context_files_response:
            for context in context_files_response:
                print(f"{YELLOW}{context}{RESET}")
        else:
            print(f"{YELLOW}None{RESET}")

    # debug_method_map["webview/postMessage"] = True

    # Cleanup the server and return None
    await cody_server.cleanup_server()
    return None


if __name__ == "__main__":
    asyncio.run(main())
