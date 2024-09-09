import asyncio
import logging
import os
from asyncio.subprocess import Process

from codypy.exceptions import (
    AgentBinaryDownloadError,
    AgentBinaryNotFoundError,
    ServerTCPConnectionError,
)
from codypy.messaging import _send_jsonrpc_request
from codypy.utils import (
    _check_for_binary_file,
    _download_binary_to_path,
    _format_binary_name,
)

logger = logging.getLogger(__name__)


async def _get_cody_binary(binary_path: str, version: str) -> str:
    print(f"Checking for Cody Agent binary at {binary_path}")
    has_agent_binary = await _check_for_binary_file(binary_path, "cody-agent", version)
    if not has_agent_binary:
        logger.warning(
            "Cody Agent binary does not exist at the specified path: %s", binary_path
        )
        logger.warning("Start downloading the Cody Agent binary")
        is_completed = await _download_binary_to_path(
            binary_path, "cody-agent", version
        )
        if not is_completed:
            raise AgentBinaryDownloadError("Failed to download the Cody Agent binary")

    return os.path.join(binary_path, await _format_binary_name("cody-agent", version))


class CodyServer:
    @classmethod
    async def init(
        cls,
        binary_path: str,
        version: str,
        use_tcp: bool = False,  # default because of ca-certificate verification
    ) -> "CodyServer":
        cody_binary = await _get_cody_binary(binary_path, version)
        cody_server = cls(cody_binary, use_tcp)
        await cody_server._create_server_connection()
        return cody_server

    def __init__(self, cody_binary: str, use_tcp: bool) -> None:
        self.cody_binary = cody_binary
        self.use_tcp = use_tcp
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
            raise AgentBinaryNotFoundError(
                "Cody Agent binary path is empty. You need to specify the "
                "BINARY_PATH to an absolute path to the agent binary or to "
                "the index.js file."
            )

        debug = logger.getEffectiveLevel() == logging.DEBUG
        os.environ["CODY_AGENT_DEBUG_REMOTE"] = str(self.use_tcp).lower()
        os.environ["CODY_DEBUG"] = str(debug).lower()

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
        args.append("api")
        args.append("jsonrpc-stdio")
        self._process: Process = await asyncio.create_subprocess_exec(
            binary,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env=os.environ,
        )
        logger.info("Cody agent process with PID %d created", self._process.pid)
        self._reader = self._process.stdout
        self._writer = self._process.stdin

        if not self.use_tcp:
            logger.info("Created a stdio connection to the Cody agent")
        else:
            retry: int = 0
            retry_attempts: int = 5
            # TODO: Consider making this configurable
            host: str = "localhost"
            port: int = 3113
            for retry in range(retry_attempts):
                try:
                    (self._reader, self._writer) = await asyncio.open_connection(
                        host, port
                    )
                    if self._reader is not None and self._writer is not None:
                        logger.info(
                            "Created a TCP connection to the Cody agent (%s:%s)",
                            host,
                            port,
                        )
                        break
                    # return reader, writer, process
                except ConnectionRefusedError as exc:
                    # TODO: This is not the nicest way to do retry but it
                    # keeps the logging sane. Consider refactoring.
                    await asyncio.sleep(1)  # Retry after a short delay
                    retry += 1
                    if retry == retry_attempts:
                        logger.debug(
                            "Exhausted %d retry attempts while trying to connect to %s:%s",
                            retry_attempts,
                            host,
                            port,
                        )
                        raise ServerTCPConnectionError(
                            "Could not connect to server: %s:%s", host, port
                        ) from exc
                    else:
                        logger.debug(
                            "Connection to %s:%s failed, retrying (%d)",
                            host,
                            port,
                            retry,
                        )

    async def cleanup_server(self):
        """
        Cleans up the server connection by sending a "shutdown" request to the server and terminating the server process if it is still running.
        """
        logger.info("Cleaning up Server...")
        await _send_jsonrpc_request(self._writer, "shutdown", None)
        if self._process.returncode is None:
            self._process.terminate()
        await self._process.wait()
