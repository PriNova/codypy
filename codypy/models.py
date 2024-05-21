"""
CodyPy data models
------------------

These classes are representing Cody agent response objects or other
configuration items.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Dict, Literal

from pydantic import AliasChoices, BaseModel, Field, ValidationError, validator


class ExtensionConfiguration(BaseModel):
    """Agent extension configuration

    :param accessToken: String, token used to talk to Sourcegraph
    :param serverEndpoint: String, hostname of the Sourcegraph instance.
                           Default: https://sourcegraph.com
    :param proxy: (optional) String, address of the proxy URL
    :param codebase: (optional) String, unknown
    :param customHeaders: (optional) Dict, send custom HTTP headers
    :param anonymousUserID: (optional) String, used in telemetry events
        anonymousUserID is an important component of telemetry events that get
        recorded. It is currently optional for backwards compatibility, but
        it is strongly recommended to set this when connecting to Agent.
    :param autocompleteAdvancedProvider: (optional) String, unknown
    :param debug: (optional) Bool, enable agent binary debugging
    :param verboseDebug: (optional) Bool, enable agent binary debugging
    :param customConfiguration: (optional) Dict, unknown
    """

    accessToken: str = ""
    serverEndpoint: str = "https://sourcegraph.com"
    codebase: str = ""
    proxy: str | None = None
    customHeaders: Dict[str, str] = {}
    anonymousUserID: str | None = None
    autocompleteAdvancedProvider: str | None = None
    autocompleteAdvancedModel: str | None = None
    debug: bool | None = None
    verboseDebug: bool | None = None
    customConfiguration: Dict | None = None


class ClientCapabilities(BaseModel):
    """Agent client capabilities"""

    completions: Literal["none"] = "none"
    chat: Literal["none", "streaming"] = "none"
    git: Literal["none", "disabled"] = "none"
    progressBars: Literal["none", "enabled"] = "none"
    edit: Literal["none", "enabled"] = "none"
    editWorkspace: Literal["none", "enabled"] = "none"
    untitledDocuments: Literal["none", "enabled"] = "none"
    showDocument: Literal["none", "enabled"] = "none"
    codeLenses: Literal["none", "enabled"] = "none"
    showWindowMessage: Literal["notification", "request"] = "notification"


class AgentSpecs(BaseModel):
    """Agent specification

    :param name: String, name of the agent
    :param version: String, version of the client agent
    :param workspaceRootUri: (optional) String, root path of the code workspace
    :param extensionConfiguration: ExtensionConfiguration instance
    :param capabilities: ClientCapabilities instance
    """

    name: str = "codypy-agent"
    version: str = "0.0.5b"
    workspaceRootUri: str = ""
    extensionConfiguration: ExtensionConfiguration = Field(
        default_factory=ExtensionConfiguration
    )
    capabilities: ClientCapabilities = Field(default_factory=ClientCapabilities)


@dataclass
class ModelSpec:
    """LLM Model Specification

    :param model_name: String, name of the model.
    :param model_id: String, Sourcegraph ID of the model.
    :param temperature: (optional) Float, Defaults to 0.0
    :param maxTokensToSample: (optional) Int, Defaults to 512
    """

    model_name: str = ""
    model_id: str = ""
    temperature: float = 0.0
    maxTokensToSample: int = 512  # pylint: disable=invalid-name


# pylint: disable=invalid-name
class Models(Enum):
    """LLM Model ENUM"""

    Claude2 = ModelSpec(
        model_name="Claude 2.0",
        model_id="anthropic/claude-2.0",
    )
    Claude2_1 = ModelSpec(
        model_name="Claude 2.1",
        model_id="anthropic/claude-2.1",
    )
    Claude1_2Instant = ModelSpec(
        model_name="Claude 1.2 Instant",
        model_id="anthropic/claude-instant-1.2",
    )
    Claude3Haiku = ModelSpec(
        model_name="Claude 3 Haiku",
        model_id="anthropic/claude-3-haiku-20240307",
    )
    Claude3Sonnet = ModelSpec(
        model_name="Claude 3 Sonnet",
        model_id="anthropic/claude-3-sonnet-20240229",
    )
    Claude3Opus = ModelSpec(
        model_name="Claude 3 Opus",
        model_id="anthropic/claude-3-opus-20240229",
    )
    GPT35Turbo = ModelSpec(
        model_name="GPT-3.5 Turbo",
        model_id="openai/gpt-3.5-turbo",
    )
    GPT4TurboPreview = ModelSpec(
        model_name="GPT-4 Turbo",
        model_id="openai/gpt-4-turbo",
    )
    Mixtral8x7b = ModelSpec(
        model_name="Mixtral 8x7b",
        model_id="fireworks/accounts/fireworks/models/mixtral-8x7b-instruct",
    )
    Mixtral8x22b = ModelSpec(
        model_name="Mixtral 8x22b Preview",
        model_id="fireworks/accounts/fireworks/models/mixtral-8x22b-instruct-preview",
    )


class CodyLLMSiteConfiguration(BaseModel):
    """Model for the LLM Site configuration"""

    chatModel: str | None = None
    chatModelMaxTokens: int | None = None
    fastChatModel: str | None = None
    fastChatModelMaxTokens: int | None = None
    completionModel: str | None = None
    completionModelMaxTokens: int | None = None
    provider: str | None = None


class AuthStatus(BaseModel):
    """Model for the AuthStatus response"""

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
    """Model for the initialized Cody Agent specification"""

    name: str
    authenticated: bool | None = None
    codyEnabled: bool | None = None
    codyVersion: str | None = None
    authStatus: AuthStatus | None = None


class Message(BaseModel):
    """Chat Message model

    :param text: String, contains the answer or the question
    :param speaker: String, could be either "human" or "assistant".
                    Signals which end sent the text.
    :param contextFiles: (optional) List[String], if the answer did
                         reference repository context files, the files
                         will be listed in here.
    """

    text: str
    speaker: Literal["human", "assistant"]
    contextFiles: list | None = None


class Transcript(BaseModel):
    """Chat Transcript model

    :param type_name: String, it should be always "transcript"
    :param messages: List of Messga objects
    :param isMessageInProgress: Bool, signals if the message is complete.
                                This should most of the time be False as
                                we instantiate the object at the end of
                                the stream.
    :param chatID: Datetime, timestamp of the response.
    """

    type_name: Literal["transcript"] = Field(
        validation_alias=AliasChoices("type_name", "type")
    )
    messages: list[Message]
    isMessageInProgress: bool
    chatID: datetime

    @validator("chatID", pre=True)
    @classmethod
    def parse_chat_id(cls, value: str) -> datetime:
        """Validate and cast the string value into a datetime object"""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Parse the string using the appropriate format
            return datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT").astimezone(UTC)
        return ValidationError("chatID field must be a parseable datetime string")

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
