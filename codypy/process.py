"""
CodyPy ProcessManager implementation
------------------------------------

This module contains the CodyProcessManager class implementation.
It is responsible for managing the Cody node agent binary process
and map to the process' stdio or TCP sockets.
"""

import asyncio
import logging
import os
from asyncio.subprocess import Process

logger = logging.getLogger(__name__)


class CodyProcessManager:
    """Spawn a cody agent process and expose the reader/writer socket"""

    def __init__(self, binary_path: str, binary_args: tuple[str, ...], use_tcp: bool):
        self.binary_path = binary_path
        self.binary_args = binary_args
        self.use_tcp = use_tcp
        self.process: Process | None = None
        self.reader = None
        self.writer = None

    async def create_process(self) -> None:
        """Asynchronously creates a connection to the Cody server"""
        env_vars = os.environ.copy()
        debug = logger.getEffectiveLevel() == logging.DEBUG
        env_vars["CODY_DEBUG"] = str(debug).lower()
        env_vars["CODY_AGENT_DEBUG_REMOTE"] = str(self.use_tcp).lower()

        self.process = await asyncio.create_subprocess_exec(
            self.binary_path,
            *self.binary_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env=env_vars,
        )
        self.reader = self.process.stdout
        self.writer = self.process.stdin
        logger.info("Cody agent process with PID %d created", self.process.pid)

        if self.use_tcp:
            await self._initialize_tcp_connection()
        else:
            logger.info("Created a stdio connection to the Cody agent.")

    async def _initialize_tcp_connection(self):
        logger.info("Initializing TCP connection to the Cody agent.")
        retry_attempts = 5
        for _ in range(retry_attempts):
            try:
                self.reader, self.writer = await asyncio.open_connection(
                    "localhost", 3113
                )
                if self.reader and self.writer:
                    logger.info("Connected to server: localhost:3113")
                    return
            except ConnectionRefusedError:
                await asyncio.sleep(1)
        raise ConnectionRefusedError(
            f"Failed to connect to localhost:3113 after {retry_attempts} attempts."
        )

    async def close(self):
        """Terminate the process"""
        if self.process:
            if self.use_tcp:
                logger.debug("Closing TCP connection to Cody agent")
                self.writer.close()
            if self.process.returncode is None:
                logger.info(
                    "Terminating Cody agent process with PID %d", self.process.pid
                )
                self.process.terminate()
            await self.process.wait()
