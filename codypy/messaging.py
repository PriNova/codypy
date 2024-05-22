"""
CodyPy Agent implementation
---------------------------

This module contains the RCPClient class implementation.
The object is responsible to handle JsonRPC read/write operations via
the connected reader/writer sockets.
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict

import pydantic_core as pd

logger = logging.getLogger(__name__)


class RPCDriver:
    """Class to handle all RPC communications"""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.message_id: int = 1
        self.reader: asyncio.StreamReader = reader
        self.writer: asyncio.StreamWriter = writer

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
        json_message: str = pd.to_json(message).decode()
        content_length: int = len(json_message)
        content_message: str = f"Content-Length: {content_length}\r\n\r\n{json_message}"

        # Send the JSON-RPC message to the server
        self.writer.write(content_message.encode("utf-8"))
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
            self.reader.readuntil(b"\r\n\r\n"), timeout=5.0
        )
        content_length: int = int(
            headers.decode("utf-8").split("Content-Length:")[1].strip()
        )

        json_data: bytes = await asyncio.wait_for(
            self.reader.readexactly(content_length), timeout=5.0
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
                yield pd.from_json(response)
        except asyncio.TimeoutError:
            yield pd.from_json("{}")

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
        await self.send_jsonrpc_request(method_name, params)
        async for response in self.handle_server_respones():
            logger.debug("Response: %s", response)
            if response and "result" in response:
                logger.debug("Messaging: request_response: %s", response)
                return response["result"]
        return None
