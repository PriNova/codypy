"""
codypy.messaging

Contains the RCPClient class to read/write jsonrpc from/to the agent
socket
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, Tuple

import pydantic_core as pd

logger = logging.getLogger(__name__)


class RPCClient:
    """Class to handle all RPC communications"""

    def __init__(self):
        self.message_id = 1
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None

    async def _send_jsonrpc_request(
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

    async def _handle_server_respones(self) -> AsyncGenerator[Dict[str, Any], Any]:
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

    @staticmethod
    async def _show_last_message(
        messages: Dict[str, Any], show_context_files: bool
    ) -> Tuple[str, str, list[str]]:
        """
        Retrieves the speaker and text of the last message in a transcript.

        Args:
            messages (Dict[str, Any]): A dictionary containing the message history.

        Returns:
            Tuple[str, str]: A tuple containing the speaker and text of the last message.
        """
        if messages is not None and messages["type"] == "transcript":
            last_message = messages["messages"][-1:][0]
            logger.debug(last_message)
            speaker: str = last_message["speaker"]
            text: str = last_message["text"]

            context_file_results = []
            if show_context_files:
                context_files: list[any] = messages["messages"]

                for context_result in context_files:
                    res = (
                        context_result["contextFiles"]
                        if "contextFiles" in context_result
                        else []
                    )
                    for reso in res:
                        uri = reso["uri"]["path"]
                        if "range" in reso:
                            rng = reso["range"]
                            rng_start = rng["start"]["line"]
                            rng_end = rng["end"]["line"]
                            context_file_results.append(f"{uri}:{rng_start}-{rng_end}")

            return speaker, text, context_file_results
        return ("", "", [])

    @staticmethod
    async def _show_messages(message) -> None:
        """
        Prints the speaker and text of each message in a transcript.

        Args:
            message (dict): A dictionary containing the message history, with a "type" key set to
                            "transcript" and a "messages" key containing
                            a list of message dictionaries.
        Returns:
            None
        """
        if message["type"] == "transcript":
            for msg in message["messages"]:
                if configs.IS_DEBUGGING:
                    output = f"{msg['speaker']}: {msg['text']}\n"
                    print(output)

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
        await self._send_jsonrpc_request(method_name, params)
        async for response in self._handle_server_respones():
            if response and "result" in response:
                logger.debug("Messaging: request_response: %s", response)
                return response["result"]
        return None
