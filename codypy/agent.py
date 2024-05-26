"""
CodyPy Agent implementation
---------------------------

This module contains the CodyAgent class implementation.
The object takes care of all RPC communication via a CodyServer
instance.
"""

import logging
import warnings
from datetime import UTC, datetime
from typing import Any, Self

from .chat import Chat
from .models import AgentSpecs, Message, PlainMessage
from .server import CodyServer

logger = logging.getLogger(__name__)


class CodyAgent:
    """Cody agent implementing various RPC functions"""

    def __init__(self, server: CodyServer, agent_specs: AgentSpecs):
        self.server: CodyServer = server
        self.agent_specs: AgentSpecs = agent_specs
        self.repos: dict = {}
        self.chats: list[Chat] = []
        self.root_chat: Chat | None = None

    @classmethod
    async def init(  # pylint: disable=too-many-arguments
        cls,
        binary_path: str,
        access_token: str = "",
        server_endpoint: str = "https://sourcegraph.com",
        agent_specs: AgentSpecs | None = None,
        use_tcp: bool = False,
    ) -> Self:
        """Initialize a CodyAgent instance ready to be used

        :param binary_path: String, path to the cody agent binary
        :param access_token: String, the access token for Cody
        :param server_endpoint: (optional) String, Sourcegraph instance URL
                                Default: https://sourcegraph.com
        :param agent_specs: (optional) AgentSpecs instance, allows you to
                            initialize the agent with fully customised specs
        :param use_tcp: (optional) Bool, when connectiong to the process
                        use TCP connection instead of stdio (Default: False)

        This call will perform all the necessary steps to setup a fully
        ready CodyAgent instance:
        1. Create a CodyServer instance
        2. Spawn a new Cody agent process
        3. Connect the RCP driver to the i/o of the process
        4. Perform the agent initialization (which includes authentication)
        5. Return the ready agent instance
        """

        if not access_token and not server_endpoint:
            raise ValueError(
                "Either `access_token` or `agent_specs` should be specified to"
                "initialize an agent"
            )
        server = CodyServer(cody_binary=binary_path, use_tcp=use_tcp)
        await server.process_manager.create_process()
        server.init_rpc_driver()
        if not agent_specs:
            logger.debug("Initializing AgentSpecs with defaults")
            agent_specs = AgentSpecs(
                extensionConfiguration={
                    "accessToken": access_token,
                    "serverEndpoint": server_endpoint,
                },
            )
        await server.initialize(agent_specs=agent_specs)
        return cls(server=server, agent_specs=agent_specs)

    async def initialize_agent(self, is_debugging: bool | None = False) -> None:
        """Initializes the Cody agent by sending an "initialize" request
        to the agent and handling the response.

        The method takes in agent specifications, a debug method map,
        and a boolean flag indicating whether debugging is enabled. It
        returns the initialized CodyAgentSpecs if the server is
        authenticated, otherwise raise exception.

        The method first creates a callback function that validates the
        response from the "initialize" request, prints the agent
        information if debugging is enabled, and checks if the server is
        authenticated. If the server is not authenticated, the method
        calls cleanup_server and returns None.

        Finally, the method calls request_response to send the "initialize"
        request with the agent specifications, the debug method map, the
        reader and writer streams, the debugging flag, and the callback
        function.
        """
        warnings.warn(
            "initialize_agent() method will be removed. Use CodyAgent.init() instead",
            DeprecationWarning,
        )
        if is_debugging is not None:
            warnings.warn(
                "`is_debugging` is deprecated and ignored. The binary debug "
                "flag is controlled by the configured logging level.",
                DeprecationWarning,
            )
        await self.server.initialize(agent_specs=self.agent_specs)

    async def close(self):
        """Cleanup Cody server gracfully"""
        await self.server.close()

    async def rpc(self, method: str, params: dict):
        """Shortcut for making RPC calls via the server -> RPCDriver"""
        return await self.server.rpc_driver.request_response(method, params)

    async def new_chat(self, is_debugging: bool = None) -> Chat:
        """Initiates a new chat session with the Cody agent server."""
        if is_debugging is not None:
            warnings.warn(
                "`is_debugging` is deprecated and ignored. The binary debug "
                "flag is controlled by the configured logging level.",
                DeprecationWarning,
            )
        new_chat_id = await self.rpc("chat/new", None)
        chat = Chat(chat_id=new_chat_id, agent=self)
        if not self.root_chat:
            self.root_chat = chat
        self.chats.append(chat)
        return chat

    async def restore_chat(
        self, messages: list[dict[str, str] | Message | PlainMessage]
    ) -> Chat:
        """Restore a conversation from an existing message stack

        :param messages: List of Dicts, Message or PlainMessage objects
            To restore a chat session to Cody we need to construct a list
            of dictionaries which contains two keys: "text" and "speaker".
            This is almost the same as the Message object without the
            contextFile field.
        """
        panel_id = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
        clean_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                plain_msg = PlainMessage(**msg)
            elif isinstance(msg, Message):
                plain_msg = PlainMessage(**msg.model_dump())
            elif isinstance(msg, PlainMessage):
                plain_msg = msg
            else:
                raise ValueError(
                    "`messages` parameter should be a list of dicts or Message objects"
                )
            clean_messages.append(plain_msg.model_dump())
        params = {"messages": clean_messages, "chatID": panel_id}
        new_chat_id = await self.rpc("chat/restore", params)
        chat = Chat(chat_id=new_chat_id, agent=self)
        self.chats.append(chat)
        return chat

    async def lookup_repo_ids(self, repos: list[str]) -> list[dict]:
        """Lookup repository objects via their names

        Results are cached in self.repos dictionary to avoid extra
        lookups if context is changed.

        Args:
            context_repos (list of strings):
                Name of the repositories which should be used for the
                chat context.

        Example:
        >>> client._lookup_repo_ids(["github.com/jsmith/awesomeapp"])
        [{"name":"github.com/jsmith/awesomeapp","id":"UmVwb3NpdG9yeToxMjM0"}]
        """

        if repos_to_lookup := [x for x in repos if x not in self.repos]:
            params = {"names": repos_to_lookup, "first": len(repos_to_lookup)}
            response = await self.rpc("graphql/getRepoIds", params)
            for repo in response["repos"]:
                self.repos[repo["name"]] = repo
            # If repo was not found, add it to the cache with a None
            # to avoid further lookups.
            for repo in repos:
                if repo not in self.repos:
                    self.repos[repo] = None

        return [self.repos[x] for x in repos if self.repos[x]]

    async def get_models(self, model_type: str) -> Any:
        """Retrieves the available models for the specified model
        type (either "chat" or "edit") from the Cody agent server.

        Args:
            model_type (Literal["chat", "edit"]):
                The type of model to retrieve.

        Returns:
            Any: The result of the "chat/models" request.
        """

        model = {"modelUsage": model_type}
        return await self.rpc("chat/models", model)

    async def get_remote_repositories(self, repo_id: str) -> Any:
        """Shortcut to get remote repositories"""
        return await self.rpc("chat/remoteRepos", repo_id)

    async def chat(self, **kwargs):
        """Shortcut to access the root chat's ask() method"""
        kwargs.pop("is_debugging")
        kwargs.pop("show_context_files")
        return await self.root_chat.ask(**kwargs)

    async def set_model(self, **kwargs):
        """Shortcut to access the root chat's set_model() method"""
        kwargs.pop("is_debugging")
        return await self.root_chat.ask(**kwargs)
