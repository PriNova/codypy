import asyncio
import os
import sys
from asyncio.subprocess import Process

from codypy.config import RED, RESET, YELLOW
from codypy.logger import log_message
from codypy.messaging import _send_jsonrpc_request
from codypy.utils import (
    _check_for_binary_file,
    _download_binary_to_path,
    _format_binary_name,
)


async def _get_cody_binary(binary_path: str, version: str) -> str:
    has_agent_binary = await _check_for_binary_file(binary_path, "cody-agent", version)
    if not has_agent_binary:
        print(
            f"{YELLOW}WARNING: The Cody Agent binary does not exist at the specified path: {binary_path}{RESET}"
        )
        print(f"{YELLOW}WARNING: Start downloading the Cody Agent binary...{RESET}")
        is_completed = await _download_binary_to_path(
            binary_path, "cody-agent", version
        )
        if not is_completed:
            print(f"{RED}ERROR: Failed to download the Cody Agent binary.{RESET}")
            sys.exit(1)

    return os.path.join(binary_path, await _format_binary_name("cody-agent", version))


class CodyServer:
    @classmethod
    async def init(
        cls,
        binary_path: str,
        version: str,
        use_tcp: bool = False,  # default because of ca-certificate verification
        is_debugging: bool = False,
    ) -> "CodyServer":
        cody_binary = await _get_cody_binary(binary_path, version)
        cody_server = cls(cody_binary, use_tcp, is_debugging)
        await cody_server._create_server_connection()
        return cody_server

    def __init__(self, cody_binary: str, use_tcp: bool, is_debugging: bool) -> None:
        self.cody_binary = cody_binary
        self.use_tcp = use_tcp
        self.is_debugging = is_debugging
        self._process: Process | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def _create_server_connection(
        self, test_against_node_source: bool = False
    ) -> None:
        """
        Asynchronously creates a connection to the Cody server.
        If `cody_binary` is an empty string, it prints an error message and exits the program.
        Sets the `CODY_AGENT_DEBUG_REMOTE` and `CODY_DEBUG` environment variables based on the `use_tcp` and `is_debugging` flags, respectively.
        Creates a subprocess to run the Cody agent, either by executing the `bin/agent` binary or running the `index.js` file specified by `binary_path`.
        Depending on the `use_tcp` flag, it either connects to the agent using stdio or opens a TCP connection to `localhost:3113`.
        If the TCP connection fails after 5 retries, it prints an error message and exits the program.
        Returns the reader and writer streams for the agent connection.
        """
        if not test_against_node_source and self.cody_binary == "":
            log_message(
                "CodyServer: _create_server_connection:",
                "ERROR: The Cody Agent binary path is empty.",
            )
            print(
                f"{RED}You need to specify the BINARY_PATH to an absolute path to the agent binary or to the index.js file. Exiting...{RESET}"
            )
            sys.exit(1)

        os.environ["CODY_AGENT_DEBUG_REMOTE"] = str(self.use_tcp).lower()
        os.environ["CODY_DEBUG"] = str(self.is_debugging).lower()

        args = []
        binary = ""
        if test_against_node_source:
            binary = "node"
            args.extend(
                (
                    "--enable-source-maps",
                    "/home/prinova/CodeProjects/cody/agent/dist/index.js",
                )
            )
        else:
            binary = self.cody_binary
        args.append("jsonrpc")
        self._process: Process = await asyncio.create_subprocess_exec(
            binary,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env=os.environ,
        )

        self._reader = self._process.stdout
        self._writer = self._process.stdin

        if not self.use_tcp:
            log_message(
                "CodyServer: _create_server_connection:",
                "Created a stdio connection to the Cody agent.",
            )
            if self.is_debugging:
                print(f"{YELLOW}--- stdio connection ---{RESET}")
            self._reader = self._process.stdout
            self._writer = self._process.stdin

        else:
            log_message(
                "CodyServer: _create_server_connection:",
                "Created a TCP connection to the Cody agent.",
            )
            if self.is_debugging:
                print(f"{YELLOW}--- TCP connection ---{RESET}")
            retry: int = 0
            retry_attempts: int = 5
            for retry in range(retry_attempts):
                try:
                    (self._reader, self._writer) = await asyncio.open_connection(
                        "localhost", 3113
                    )
                    if self._reader is not None and self._writer is not None:
                        log_message(
                            "CodyServer: _create_server_connection:",
                            "Connected to server: localhost:3113",
                        )
                        print(f"{YELLOW}Connected to server: localhost:3113{RESET}\n")
                        break

                    # return reader, writer, process
                except ConnectionRefusedError:
                    await asyncio.sleep(1)  # Retry after a short delay
                    retry += 1
            if retry == retry_attempts:
                log_message(
                    "CodyServer: _create_server_connection:",
                    "Could not connect to server. Exiting...",
                )
                print(f"{RED}Could not connect to server. Exiting...{RESET}")
                sys.exit(1)

    async def cleanup_server(self):
        """
        Cleans up the server connection by sending a "shutdown" request to the server and terminating the server process if it is still running.
        """
        log_message("CodyServer: cleanup_server:", "Cleanup Server...")
        await _send_jsonrpc_request(self._writer, "shutdown", None)
        if self._process.returncode is None:
            self._process.terminate()
        await self._process.wait()
