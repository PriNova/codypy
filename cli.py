import argparse
import asyncio
import os

from codypy.client_info import AgentSpecs
from codypy.cody_py import CodyAgent, CodyServer
from codypy.config import debug_method_map


async def async_main():
    parser = argparse.ArgumentParser(description="Cody Agent Python CLI")
    parser.add_argument("chat", help="Initialize the chat conversation")
    parser.add_argument(
        "--binary_path",
        type=str,
        required=True,
        default=os.getenv("BINARY_PATH"),
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
        "-ec",
        "--enhanced-context",
        type=bool,
        default=True,
        help="Use enhanced context if in a git repo  (needs remote repo configured). Default=True",
    )
    parser.add_argument(
        "-sc",
        "--show-context",
        type=bool,
        default=False,
        help="Show the inferred context files from the message if any. Default=True",
    )

    args = parser.parse_args()
    await chat(args)


async def chat(args):
    cody_server: CodyServer = await CodyServer.init(
        binary_path=args.binary_path, version="0.0.5b", is_debugging=False
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
        agent_specs=agent_specs, is_debugging=False
    )

    await cody_agent.new_chat(is_debugging=False)

    debug_method_map["webview/postMessage"] = False
    response = await cody_agent.chat(
        message=args.message,
        enhanced_context=args.ec,
        show_context_files=args.sc,
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
