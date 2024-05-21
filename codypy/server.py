"""
CodyPy Server implementation
----------------------------

This module contains the CodyServer class implementation.
CodyServer joins two other components: CodyProcessManager
and RPCDriver.
"""

import logging
import os
import warnings
from typing import Self

from .messaging import RPCDriver
from .models import AgentSpecs, CodyAgentSpecs
from .process import CodyProcessManager

logger = logging.getLogger(__name__)


class CodyServer:
    """Asynchronous I/O wrapper around Cody agent binary to make RPC calls

    :param cody_binary str: Path of the Cody agent binary
        To test against the cody agent source, you have set `cody_binary` as
        an empty string and set CODYPY_CODY_CMD environment variable with the
        full node command.
    :use_tcp bool: Enables agent communication via TCP socket via env var
                   CODY_AGENT_DEBUG_REMOTE. By default this is turned off
                   and communication is via process stdin/stdout.
    """

    def __init__(self, cody_binary: str, use_tcp: bool = False) -> None:
        self.process_manager: CodyProcessManager = CodyProcessManager(
            *self._prepare_binary(cody_binary), use_tcp
        )
        self.rpc_driver: RPCDriver | None = None

    @classmethod
    async def init(
        cls,
        binary_path: str,
        version: str = "",
        use_tcp: bool = False,
        is_debugging: bool | None = None,
    ) -> Self:
        """Wrapper to asynchronously initialize a CodyServer instance

        This call will instantiate a CodyServer instance, create a
        Cody agent process in the background, and map the i/o handlers
        to the RPC driver.

        :param binary_path: String, path to the Cody agent binary
        :param version: (optional, deprecated): The version string of the
                        agent binary.
                        This argument will be deprecated.
        :param use_tcp: (optional) Bool, controls if we should communicate
                        to the Cody agent process via TCP or stdio sockets
        :param is_debugging: (optional) Bool, controls if debug log should
                             be enabled.
                             This argument will be deprecated.
        """

        if version:
            warnings.warn(
                "`version` argument is deprecated and ignored", DeprecationWarning
            )
        if is_debugging is not None:
            warnings.warn(
                "`is_debugging` is deprecated and ignored. The binary debug "
                "flag is controlled by the configured logging level.",
                DeprecationWarning,
            )
        server = cls(cody_binary=binary_path, use_tcp=use_tcp)
        await server.process_manager.create_process()
        server.init_rpc_driver()
        return server

    @staticmethod
    def _prepare_binary(cody_binary: str) -> tuple[str, tuple[str, ...]]:
        """Find the right binary to use with the commands

        This function is mainly here to enable testability against
        Cody agent node source code directly instead of the binary

        In order to test against the compiled Cody agent source code,
        you can set CODYPY_CODY_CMD environment variable. Example:
        export CODYPY_CODY_CMD="node --enable-source-maps ~/CodeProjects/cody/agent/dist/index.js"
        """

        if custom_cmd := os.getenv("CODYPY_CODY_CMD"):
            logger.warning("Using custom cody command: %s", custom_cmd)
            tokens = custom_cmd.split(" ")
            return tokens[0], tuple(tokens[1:] + ["jsonrpc"])

        if not os.path.isfile(cody_binary):
            raise FileNotFoundError(
                "Cody binary at %s not found. Either fix the path "
                "or download the binary with `codypy download`"
            )
        return cody_binary, ("jsonrpc",)

    def init_rpc_driver(self) -> None:
        """Mounting the process i/o handlers to the RPC driver"""
        if not self.process_manager.process:
            raise ValueError("Cody agent process is not running")
        assert self.process_manager.reader is not None
        assert self.process_manager.writer is not None
        self.rpc_driver = RPCDriver(
            self.process_manager.reader,
            self.process_manager.writer,
        )

    async def initialize(self, agent_specs: AgentSpecs) -> None:
        """
        Initializes the Cody agent by sending an "initialize" request
        to the agent and handling the response.

        The method first creates a callback function that validates the
        response from the "initialize" request, prints the agent
        information if debugging is enabled, and checks if the server is
        authenticated.

        If the server is not authenticated, the method calls
        cleanup_server() and returns None.

        Finally, the method calls request_response to send the
        "initialize" request with the agent specifications, the debug
        method map, the reader and writer streams, the debugging flag,
        and the callback function.
        """

        response = await self.rpc_driver.request_response(
            "initialize", agent_specs.model_dump()
        )
        cody_agent_specs: CodyAgentSpecs = CodyAgentSpecs.model_validate(response)
        logger.debug("Agent Info: %s", cody_agent_specs)
        if not cody_agent_specs.authenticated:
            logger.error("Server is not authenticated.")
            await self.close()
            raise SystemError("Failed to authenticate to Cody agent")

        logger.info("Server is authenticated.")

    async def close(self):
        """
        Cleans up the server connection by sending a "shutdown" request
        to the server and terminating the server process if it is still
        running.
        """
        logger.debug("Terminating Cody agent server...")
        await self.rpc_driver.send_jsonrpc_request("shutdown", None)
        await self.process_manager.close()
