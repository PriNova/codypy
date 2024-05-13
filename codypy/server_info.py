from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


class CodyLLMSiteConfiguration(BaseModel):
    chatModel: str | None = None
    chatModelMaxTokens: int | None = None
    fastChatModel: str | None = None
    fastChatModelMaxTokens: int | None = None
    completionModel: str | None = None
    completionModelMaxTokens: int | None = None
    provider: str | None = None


class AuthStatus(BaseModel):
    endpoint: str
    isDotCom: bool
    isLoggedIn: bool
    showInvalidAccessTokenError: bool
    authenticated: bool
    hasVerifiedEmail: bool
    requiresVerifiedEmail: bool
    siteHasCodyEnabled: bool
    siteVersion: str
    userCanUpgrade: bool
    username: str
    primaryEmail: str
    displayName: str | None = None
    avatarURL: str
    configOverwrites: CodyLLMSiteConfiguration | None = None


class CodyAgentSpecs(BaseModel):
    name: str
    authenticated: bool | None = None
    codyEnabled: bool | None = None
    codyVersion: str | None = None
    authStatus: AuthStatus | None = None


class Message(BaseModel):
    text: str
    speaker: Literal["human", "assistant"]
    contextFiles: list | None = None


class Transcript(BaseModel):
    type_name: Literal["transcript"] = Field(
        validation_alias=AliasChoices("type_name", "type")
    )
    messages: list[Message]
    isMessageInProgress: bool
    chatID: str

    @property
    def question(self) -> str:
        """Return the last 'human' message text"""
        last_msg = self.messages[-2]
        assert last_msg.speaker == "human"
        return last_msg.text

    @property
    def answer(self) -> str:
        """Return the last 'assistant' message text"""
        last_msg = self.messages[-1]
        assert last_msg.speaker == "assistant"
        return last_msg.text
