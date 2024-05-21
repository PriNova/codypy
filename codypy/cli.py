"""
Simple CLI wrapper to interact with Cody from shell
"""

import argparse
import asyncio
import logging
import os
import sys

from .agent import CodyAgent
from .chat import Chat
from .models import AgentSpecs, Transcript
from .utils import _download_binary_to_path


def get_args() -> argparse.Namespace:
    """Create an argument parser"""

    parser = argparse.ArgumentParser(description="Cody Agent Python CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("ask", help="Ask a question")
    subparsers.add_parser("chat", help="Start a chat session")
    subparsers.add_parser("download", help="Download resources from the server")

    parser.add_argument(
        "--binary_path",
        type=str,
        default=os.getenv("BINARY_PATH"),
        help="The path to the Cody Agent binary. (Required)",
    )
    parser.add_argument(
        "--access_token",
        type=str,
        default=os.getenv("SRC_ACCESS_TOKEN"),
        help=(
            "The Sourcegraph access token. Can be specified as "
            "SRC_ACCESS_TOKEN envvar (Required)"
        ),
    )
    parser.add_argument(
        "-m",
        "--message",
        type=str,
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
        help=(
            "Sourcegraph endpoint Can be specified as SRC_ENDPOINT envvar "
            "(Default: https://sourcegraph.com)"
        ),
    )
    parser.add_argument(
        "-ec",
        "--enhanced-context",
        type=bool,
        default=True,
        help=(
            "Use enhanced context if in a git repo "
            "(needs remote repo configured). Default=True"
        ),
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


async def create_chat(args: argparse.Namespace) -> Chat:
    """Create a Chat session"""

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
    # Initialize Agent
    cody_agent: CodyAgent = await CodyAgent.init(
        args.binary_path, agent_specs=agent_specs
    )
    # Create a new Chat session
    chat: Chat = await cody_agent.new_chat()
    return chat


def ask_question(args: argparse.Namespace) -> None:
    """Ask a single question from Cody synchronously"""
    if not args.binary_path:
        print(
            "error: argument binary_path: argument must be set "
            "explicitly or via BINARY_PATH envvar"
        )
        sys.exit(1)
    if not args.access_token:
        print(
            "error: argument access_token: argument must be set "
            "explicitly or via SRC_ACCESS_TOKEN envvar"
        )
        sys.exit(1)
    if not args.message:
        print("error: argument message: argument must be set")
        sys.exit(1)

    loop = asyncio.new_event_loop()
    chat: Chat = loop.run_until_complete(create_chat(args))
    try:
        reply: Transcript = loop.run_until_complete(chat.ask(args.message))
        print(f"Q: {reply.question}\nA: {reply.answer}")
    finally:
        loop.run_until_complete(chat.agent.close())


def start_chat(args: argparse.Namespace) -> None:
    """Start a chat session with Cody synchronously"""
    if not args.binary_path:
        print(
            "error: argument binary_path: argument must be set "
            "explicitly or via BINARY_PATH envvar"
        )
        sys.exit(1)
    if not args.access_token:
        print(
            "error: argument access_token: argument must be set "
            "explicitly or via SRC_ACCESS_TOKEN envvar"
        )
        sys.exit(1)
    loop = asyncio.new_event_loop()
    chat: Chat = loop.run_until_complete(create_chat(args))
    print("Write your questions below. To exit type 'exit' or hit CTRL^C")
    try:
        while True:
            if question := input("Q: "):
                if question.lower().startswith("exit"):
                    break
                reply: Transcript = loop.run_until_complete(chat.ask(question))
                print(f"A: {reply.answer}")
            else:
                print("No question asked. Try entering something or hit CTRL^C")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        loop.run_until_complete(chat.agent.close())


def main():
    """Main program"""
    args = get_args()
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(filename)s:%(funcName)s - %(message)s",
        level=getattr(logging, args.loglevel),
    )
    if args.command == "download":
        _download_binary_to_path(
            binary_path=".", cody_name="cody-agent", version="0.0.5b"
        )
    if args.command == "ask":
        ask_question(args)
    if args.command == "chat":
        start_chat(args)


if __name__ == "__main__":
    main()
