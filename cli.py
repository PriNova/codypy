import argparse
import asyncio
import os
from typing import Any, Dict

from codypy.client_info import AgentSpecs
from codypy.cody_py import CodyAgent, CodyServer
from codypy.config import get_debug_map


async def async_main():
    parser = argparse.ArgumentParser(description="Cody Agent Python CLI")
    parser.add_argument("chat", help="Initialize the chat conversation")
    parser.add_argument(
        "--binary_path",
        type=str,
        required=True,
        help="The path to the Cody Agent binary. (Required)",
    )

    parser.add_argument(
        "--access_token",
        type=str,
        required=True,
        default=os.getenv("SRC_ACCESS_TOKEN"),
        help="The Sourcegraph access token. (Needs to be exported as SRC_ACCESS_TOKEN) (Required)",
    )
    parser.add_argument(
        "-m",
        "--message",
        type=str,
        required=True,
        help="The chat message to send. (Required)",
    )
    parser.add_argument(
        "--workspace_root_uri",
        type=str,
        default=os.path.abspath(os.getcwd()),
        help=f"The current working directory. Default={os.path.abspath(os.getcwd())}",
    )

    parser.add_argument(
        "-c",
        type=bool,
        default=True,
        help="Use enhanced context if in a git repo  (needs remote repo configured). Default=True",
    )

    args = parser.parse_args()
    await chat(args)


async def chat(args):
    debug_method_map: Dict[str, Any] = await get_debug_map()
    cody_server: CodyServer = await CodyServer.init(
        binary_path=args.binary_path, is_debugging=False
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
        agent_specs=agent_specs, debug_method_map=debug_method_map, is_debugging=False
    )

    await cody_agent.new_chat(debug_method_map=debug_method_map, is_debugging=False)

    debug_method_map["webview/postMessage"] = False
    response = await cody_agent.chat(
        message=args.message,
        enhanced_context=args.c,
        debug_method_map=debug_method_map,
        is_debugging=False,
    )
    if response == "":
        return
    print(response)

    debug_method_map["webview/postMessage"] = True

    await cody_server.cleanup_server()
    return None


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
