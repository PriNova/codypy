"""
CodyPy data models
------------------

These classes are representing Cody agent response objects or other
configuration items.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, Literal, Union

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


class Position(BaseModel):
    """Model for position in context files"""

    line: int
    character: int


class Range(BaseModel):
    """Model for range in context files"""

    start: Position
    end: Position


class Uri(BaseModel):
    """Model for context file URI"""

    mid: int = Field(validation_alias=AliasChoices("mid", "$mid"))
    external: str
    path: str
    scheme: str
    authority: str
    query: str


# Source: https://github.com/sourcegraph/cody/blob/main/lib/shared/src/codebase-context/messages.ts
ContextItemSource = Literal[
    "embeddings",  # From embeddings search
    "user",  # Explicitly @-mentioned by the user in chat
    "keyword",  # From local keyword search
    "editor",  # From the current editor state and open tabs/documents
    "filename",
    "search",  # From symf search
    "unified",  # Remote search
    "selection",  # Selected code from the current editor
    "terminal",  # Output from the terminal
    "uri",  # From URI
    "package",  # From a package repository
    "history",  # From source control history
    "github",  # From Github API
]


class ContextItemCommon(BaseModel):
    """Model for generic Context item objects

    :param uri: Uri object
        The URI of the document (such as a file) where this context
        resides.
    :param range: (optional) Range object
        If only a subset of a file is included as context, the range of
        that subset.
    :param context: (optional) String
        The content, either the entire document or the range subset.
    :param repoName: (optional) String
    :param revision: (optional) String
    :param title: (optional) String
        For anything other than a file or symbol, the title to display
        (e.g., "Terminal Output").
    :param source: (optional) String Literal
        The source of this context item.
    :param size: (optional) Integer
        The token count of the item's content.
    :param isIgnored: (optional) Bool
        Whether the item is excluded by Cody Ignore.
    :param isTooLarge: (optional) Bool
        Whether the content of the item is too large to be included as
        context.
    :param provider: (optional) String
        The ID of the {@link ContextMentionProvider} that supplied this
        context item (or `undefined` if from a built-in context source
        such as files and symbols).
    """

    uri: Uri
    range: Range | None = None
    content: str = ""
    repoName: str = ""
    revision: str = ""
    title: str = ""
    source: ContextItemSource | None = None
    size: int | None = None
    isIgnored: bool | None = None
    isTooLarge: bool | None = None
    provider: str = ""


class ContextItemFile(ContextItemCommon):
    """Model for File type context item

    A file (or a subset of a file given by a range) that is included as
    context in a chat message.
    """

    type: Literal["file"]


class ContextItemSymbol(ContextItemCommon):
    """Model for Symbol type context item

    A symbol (which is a range within a file) that is included as
    context in a chat message.

    :param type: String Literal, should be always "symbol"
    :param symbolName: String
        The name of the symbol, used for presentation only
        (not semantically meaningful).
    :param kind: String Literal
        The kind of symbol, used for presentation only
        (not semantically meaningful).
    """

    type: Literal["symbol"]
    symbolName: str
    kind: Literal["class", "function", "method"]


class ContextItemPackage(ContextItemCommon):
    """Model for Package type context item

    A package repository that is included as context in a chat message.

    :param type: String Literal, should be always "package"
    :param repoID: String, the repository id for this package.
    :param title: String, the title for this package.
    :param ecosystem: String, the ecosystem for this package.
    :param name: String, the name for this package.
    """

    type: Literal["package"]
    repoID: str
    title: str
    ecosystem: str
    name: str


class ContextItemGithubPullRequest(ContextItemCommon):
    """Model for GithubPullRequest type context item

    A Github pull request that is included as context in a chat message.

    :param type: String Literal, should be always "github_pull_request"
    :param owner: String, the owner of the repository.
    :param repoName: String, the name of the repository.
    :param pullNumber: Int, the number for this pull request.
    :param title: String, the title of this pull request.
    """

    type: Literal["github_pull_request"]
    owner: str
    repoName: str
    pullNumber: int
    title: str


class ContextItemGithubIssue(ContextItemCommon):
    """Model for GithubIssue type context item

    A Github issue that is included as context in a chat message.

    :param type: String Literal, should be always "github_issue"
    :param owner: String, the owner of the repository.
    :param repoName: String, the name of the repository.
    :param issueNumber: Int, the number for this issue.
    :param title: String, the title of this issue.
    """

    type: Literal["github_issue"]
    owner: str
    repoName: str
    issueNumber: int
    title: str


class ContextItemOpenCtx(ContextItemCommon):
    """Model for OpenCtx type context item

    An OpenCtx context item returned from a provider.
    """

    type: Literal["openctx"]
    provider: Literal["openctx"]
    title: str
    uri: Uri
    providerUri: str
    description: str = ""
    data: Any | None = None


ContextItem = Union[
    ContextItemFile,
    ContextItemSymbol,
    ContextItemPackage,
    ContextItemGithubPullRequest,
    ContextItemGithubIssue,
    ContextItemOpenCtx,
]


class PlainMessage(BaseModel):
    """Chat Message model

    :param text: String, contains the answer or the question
    :param speaker: String, could be either "human" or "assistant".
                    Signals which end sent the text.
    """

    text: str
    speaker: Literal["human", "assistant"]


class Message(PlainMessage):
    """Chat Message model

    :param text: String, contains the answer or the question
    :param speaker: String, could be either "human" or "assistant".
                    Signals which end sent the text.
    :param contextFiles: (optional) List[String], if the answer did
                         reference repository context files, the files
                         will be listed in here.
    """

    contextFiles: list[ContextItem] | None = None


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
