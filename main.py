import asyncio
import os
from typing import Any, Dict

from dotenv import load_dotenv

from cody_agent_py.client_info import AgentSpecs
from cody_agent_py.cody_agent_py import CodyAgent, CodyServer
from cody_agent_py.config import get_debug_map

load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")


async def main():

    debug_method_map: Dict[str, Any] = await get_debug_map()

    print("--- Create Server Connection ---")
    cody_server: CodyServer = await CodyServer.init(
        binary_path="/home/prinova/CodeProjects/cody/agent/dist", is_debugging=True
    )

    agent_specs = AgentSpecs(
        workspaceRootUri="/home/prinova/CodeProjects/CodyAgentPy",
        extensionConfiguration={
            "accessToken": ACCESS_TOKEN,
            "codebase": "https://github.com/PriNova/CodyAgentPy",  # github.com/sourcegraph/cody",
            "customConfiguration": {},
        },
    )

    print("--- Initialize Agent ---")
    cody_agent: CodyAgent = await cody_server.initialize_agent(
        agent_specs=agent_specs, debug_method_map=debug_method_map, is_debugging=True
    )

    print("--- Retrieve Chat Models ---\n")
    models = await cody_agent.get_models(
        model_type="chat", debug_method_map=debug_method_map, is_debugging=True
    )
    print(models)

    print("--- Create new chat ---")
    await cody_agent.new_chat(debug_method_map=debug_method_map, is_debugging=True)

    print("--- Set Model ---")
    await cody_agent.set_model(
        model="openai/gpt-4-turbo-preview",
        debug_method_map=debug_method_map,
        is_debugging=True,
    )

    print("--- Send message (short) ---")
    # set this to False otherwise your terminal will be full of streaming messages
    debug_method_map["webview/postMessage"] = False

    # Wait for input from user in the CLI terminal
    message: str = input("Human: ")
    (speaker, message) = await cody_agent.chat(
        message=message,
        enhanced_context=False,
        debug_method_map=debug_method_map,
        is_debugging=False,
    )

    if speaker == "" or message == "":
        print("--- Failed to submit chat message ---")
        await cody_server.cleanup_server()
        return None

    output = f"{speaker.capitalize()}: {message}\n"
    print(output)

    debug_method_map["webview/postMessage"] = True

    await cody_server.cleanup_server()
    return None


if __name__ == "__main__":
    asyncio.run(main())
