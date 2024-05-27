import asyncio
import logging
import os

from dotenv import load_dotenv

from codypy.agent import CodyAgent
from codypy.client_info import AgentSpecs, Models
from codypy.config import BLUE, GREEN, RESET
from codypy.context import append_paths
from codypy.server import CodyServer

load_dotenv()
SRC_ACCESS_TOKEN = os.getenv("SRC_ACCESS_TOKEN")
BINARY_PATH = os.getenv("BINARY_PATH")


logger = logging.getLogger(__name__)


async def main():
    # set the global logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create a CodyServer instance and initialize it
    # with the specified binary path and debugging mode.
    logger.info("--- Create Server Connection ---")
    cody_server: CodyServer = await CodyServer.init(
        binary_path=BINARY_PATH,
        version="0.0.5b",
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
    logger.info("--- Initialize Agent ---")
    cody_agent: CodyAgent = CodyAgent(cody_server=cody_server, agent_specs=agent_specs)
    await cody_agent.initialize_agent()

    # Retrieve and print the available chat models
    logger.info("--- Retrieve Chat Models ---")
    models = await cody_agent.get_models(model_type="chat")
    logger.info("Available models: %s", models)
    # Create a new chat with the CodyAgent
    logger.info("--- Create new chat ---")
    await cody_agent.new_chat()

    # Set the chat model to Claude3Haiku
    logger.info("--- Set Model ---")
    await cody_agent.set_model(model=Models.Claude3Sonnet)

    # Set the repository context
    logger.info("--- Set context repo ---")
    await cody_agent.set_context_repo(repos=["github.com/PriNova/codypy"])

    # Send a message to the chat and print the response until the user enters '/quit'.
    logger.info("--- Send message (short) ---")

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
        )
        if response == "":
            break
        print(f"{BLUE}Assistant{RESET}: {response}\n")
        logger.info("--- Context Files ---")
        if context_files_response:
            for context in context_files_response:
                logger.info("file: %s", context)
        else:
            logger.info("No context file")

    # Cleanup the server and return None
    await cody_server.cleanup_server()
    return None


if __name__ == "__main__":
    asyncio.run(main())
