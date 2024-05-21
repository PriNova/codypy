"""
CodyPy Chat implementation
--------------------------

This module contains the Chat class implementation.
A Chat object is represention a conversation (session) with it's context.
One agent can have multiple chat session open at the same time, and each
has it's own separate context. Some methods are working on a chat context,
these are callable from the Chat directly.
"""

from typing import Any, ForwardRef

from .models import Models, Transcript

CodyAgent = ForwardRef("CodyAgent")


class Chat:
    """Cody chat session"""

    def __init__(self, chat_id: str, agent: CodyAgent) -> None:
        self.chat_id: str = chat_id
        self.agent: CodyAgent = agent
        self.repo_context: list[str] = []
        self.transcript: Transcript

    async def ask(
        self,
        message,
        enhanced_context: bool = True,
        context_files=None,
    ) -> Transcript:
        """Sends a chat message to the Cody server and returns the
        response.

        :param message: String, the message to be sent to Cody LLM.
        :param enhanced_context: (optional) Bool, instructs the LLM
                                 to use additional context when composing
                                 the response. Defaults to True.
        :param context_files: (optional) Undocumented

        :return: :class: `Transcript <Transcript>` object
        """
        if context_files is None:
            context_files = []

        chat_req = {
            "id": self.chat_id,
            "message": {
                "command": "submit",
                "text": message,
                "submitType": "user",
                "addEnhancedContext": enhanced_context,
                "contextFiles": context_files,
            },
        }
        result = await self.agent.rpc("chat/submitMessage", chat_req)
        return Transcript(**result)

    async def set_context_repo(self, repos: list[str]) -> None:
        """Set repositories to use as context

        :param repos: List of Strings. Sets the chat repository context
                      for the list of repos. Cody answers will consider
                      all files from the listed repositories.

        :return: None
        """

        if self.repo_context == repos:
            return

        self.repo_context = repos

        repo_objects = await self.agent.lookup_repo_ids(repos=repos)

        # Configure the selected repositories for the chat context
        command = {
            "id": self.chat_id,
            "message": {
                "command": "context/choose-remote-search-repo",
                "explicitRepos": repo_objects,
            },
        }
        await self.agent.rpc("webview/receiveMessage", command)

    async def set_model(self, model: Models = Models.Claude3Sonnet) -> Any:
        """
        Sets the model to be used for the chat session.

        :param model: Model instance. Sets the LLM model for this chat
                      session. Default: Models.Claude3Sonnet

        :return: dict object
        """

        command = {
            "id": self.chat_id,
            "message": {"command": "chatModel", "model": model.value.model_id},
        }
        return await self.agent.rpc("webview/receiveMessage", command)
