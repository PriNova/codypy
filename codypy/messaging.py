"""
CodyPy Agent implementation
---------------------------

This module contains the RCPClient class implementation.
The object is responsible to handle JsonRPC read/write operations via
the connected reader/writer sockets.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict

import pydantic_core as pd

logger = logging.getLogger(__name__)


class RPCDriver:
    """Class to handle all RPC communications

    :param reader: asyncio.StreamReader, a socket object to stdio or tcp
                   reader socket
    :param writer: asyncio.StreamWriter, a socket object to stdio or tcp
                   writer socket
    :param read_timeout: Float, the timeout value used to read from the
                         socket. Defaults to 10.0 the same as Cody Agent
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        read_timeout: float = 10.0,
    ):
        self.message_id: int = 1
        self.reader: asyncio.StreamReader = reader
        self.writer: asyncio.StreamWriter = writer
        self.read_timeout: float = read_timeout
        self.lock = asyncio.Lock()

    async def send_jsonrpc_request(
        self, method: str, params: Dict[str, Any] | None
    ) -> None:
        """Sends a JSON-RPC request to the server

        Args:
            method: The JSON-RPC method to call.
            params: The parameters to pass to the JSON-RPC method,
                    or None if no parameters are required.

        Raises:
            None
        """
        message: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": method,
            "params": params,
        }

        # Convert the message to JSON string
        # pd.to_json returns bytes. since we read/write bytes we need to
        # determine the length of the content as bytes because it differs
        # from the unicode length.
        json_message: bytes = pd.to_json(message)
        content_length: int = len(json_message)
        content_message: bytes = (
            f"Content-Length: {content_length}\r\n\r\n".encode() + json_message
        )

        # Send the JSON-RPC message to the server
        self.writer.write(content_message)
        await self.writer.drain()
        self.message_id += 1

    async def _receive_jsonrpc_messages(self) -> str:
        """Reads a JSON-RPC message from the provided `asyncio.StreamReader`.

        Returns:
            The JSON-RPC message as a string.

        Raises:
            asyncio.TimeoutError: If the message cannot be read within the 5 second timeout.
        """
        headers: bytes = await asyncio.wait_for(
            self.reader.readuntil(b"\r\n\r\n"), timeout=self.read_timeout
        )
        content_length: int = int(
            headers.decode("utf-8").split("Content-Length:")[1].strip()
        )

        json_data: bytes = await asyncio.wait_for(
            self.reader.readexactly(content_length), timeout=self.read_timeout
        )
        return json_data.decode("utf-8")

    async def handle_server_respones(self) -> AsyncGenerator[Dict[str, Any], Any]:
        """
        Asynchronously handles server responses by reading JSON-RPC messages
        from the provided `asyncio.StreamReader`.

        This function yields each JSON-RPC response as a dictionary, until a timeout occurs.

        Yields:
            A dictionary representing the JSON-RPC response.

        Raises:
            asyncio.TimeoutError: If a JSON-RPC message cannot be read within the 5 second timeout.
        """
        try:
            while True:
                response: str = await self._receive_jsonrpc_messages()
                # Cody backend returns unicode with unicode escape sequence
                # instead of raw bytes. While processing the response stream
                # we're also receiving partial unicode, e.g.
                # \\ud83c + \\udfce + \\ufe0. Using pd.to_json does not work
                # here but native json.loads does.
                yield json.loads(response)
        except asyncio.TimeoutError:
            logger.error("Reached timeout (%s sec) without complete read")
            yield {}

    async def request_response(
        self,
        method_name: str,
        params,
    ) -> Any:
        """
        Sends a JSON-RPC request to a server and handles the response.

        Args:
            method_name (str): The name of the JSON-RPC method to call.
            params: The parameters to pass to the JSON-RPC method.

        Returns:
            Any: The result of the JSON-RPC request, or None if no result is available.
        """
        logger.debug("Sending command: %s - %s", method_name, params)
        async with self.lock:
            await self.send_jsonrpc_request(method_name, params)
            response: dict | None = None
            async for response in self.handle_server_respones():
                logger.debug("Response: %s", response)
                if response and "result" in response:
                    logger.debug("Messaging: request_response: %s", response)
                    return response["result"]
        logger.error(
            "Failed to find a complete message with 'result' key. Last message: %s",
            response,
        )
        return None
