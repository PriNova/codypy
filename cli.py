import argparse
import asyncio
import os
from typing import Any, Dict

from codypy.client_info import AgentSpecs
from codypy.cody_py import CodyAgent, CodyServer
from codypy.config import get_debug_map


async def main():
    parser = argparse.ArgumentParser(description="Cody Agent Python CLI")
    parser.add_argument(
            "chat", help="Initialize the chat conversation"
        )
    parser.add_argument(
        "--binary_path",
        type=str,
        required=True,
        help="The path to the Cody Agent binary.",
    )
    
    parser.add_argument(
        "--access_token",
        type=str,
        default=os.getenv("SRC_ACCESS_TOKEN"),
        help="The Sourcegraph access token.",
    )
    parser.add_argument(
        "--workspace_root_uri",
        type=str,
        default=os.path.abspath(os.getcwd()),
        help="The current working directory.",
    )
    parser.add_argument(
        "-m",
        type=str,
        required=True,
        help="The chat message to send.",
    )

    args = parser.parse_args()
    await chat(args)


async def chat(args):
    debug_method_map: Dict[str, Any] = await get_debug_map()
    cody_server: CodyServer = await CodyServer.init(
        binary_path=args.binary_path, is_debugging=True
    )
    # Create an AgentSpecs instance with the specified workspace root URI and extension configuration.
    agent_specs = AgentSpecs(
        workspaceRootUri=args.workspace_root_uri,
        extensionConfiguration={
            "accessToken": args.access_token,
            "codebase": "",  # github.com/sourcegraph/cody",
            "customConfiguration": {},
        },
    )
    cody_agent: CodyAgent = await cody_server.initialize_agent(
        agent_specs=agent_specs, debug_method_map=debug_method_map, is_debugging=True
    )
    
    await cody_agent.new_chat(debug_method_map=debug_method_map, is_debugging=True)
    
    debug_method_map["webview/postMessage"] = False
    response = await cody_agent.chat(
            message=args.m,
            enhanced_context=True,
            debug_method_map=debug_method_map,
            is_debugging=False,
    )
    if response == "":
        return
    print(response)
    
    debug_method_map["webview/postMessage"] = True
    
    await cody_server.cleanup_server()
    return None

if __name__ == "__main__":
    asyncio.run(main())
