"""
Simple CLI wrapper to interact with Cody from shell
"""

import argparse
import asyncio
import logging
import os

from .client_info import AgentSpecs
from .cody_py import CodyAgent, CodyServer
from .config import debug_method_map


def get_args() -> argparse.Namespace:
    """Create an argument parser"""

    parser = argparse.ArgumentParser(description="Cody Agent Python CLI")
    parser.add_argument(
        "chat", help="Initialize the chat conversation", action="store_true"
    )
    parser.add_argument(
        "download", help="Download the cody-agent binary", action="store_true"
    )
    parser.add_argument(
        "--binary_path",
        type=str,
        required=False,
        default=os.getenv("BINARY_PATH"),
        help="The path to the Cody Agent binary. (Required)",
    )
    parser.add_argument(
        "--access_token",
        type=str,
        required=False,
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
        "--endpoint",
        type=str,
        default=os.getenv("SRC_ENDPOINT", "https://sourcegraph.com"),
        help="Sourcegraph endpoint (Default: https://sourcegraph.com)",
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
    parser.add_argument(
        "--loglevel",
        help="Set the log level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="WARNING",
    )

    return parser.parse_args()


async def chat(args: argparse.Namespace):
    """Send a chat message to cody and retrieve the response"""

    # Create a CodyServer instance
    cody_server: CodyServer = CodyServer(cody_binary=args.binary_path)
    await cody_server.connect()

    # Create an AgentSpecs instance with the specified workspace root URI
    # and extension configuration.
    agent_specs = AgentSpecs(
        workspaceRootUri=args.workspace_root_uri,
        extensionConfiguration={
            "accessToken": args.access_token,
            "serverEndpoint": args.endpoint,
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
        enhanced_context=args.enhanced_context,
        show_context_files=args.show_context,
        is_debugging=False,
    )
    if response == "":
        return
    print(response)

    debug_method_map["webview/postMessage"] = True

    await cody_server.cleanup_server()
    return None


def main():
    """Main program"""
    args = get_args()
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(filename)s:%(funcName)s - %(message)s",
        level=getattr(logging, args.loglevel),
    )
    asyncio.run(chat(args))


if __name__ == "__main__":
    main()
