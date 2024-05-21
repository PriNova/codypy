from dataclasses import dataclass
from enum import Enum
from typing import Dict, Literal

from pydantic import BaseModel


class ExtensionConfiguration(BaseModel):
    accessToken: str = ""
    serverEndpoint: str = "https://sourcegraph.com"
    codebase: str | None = None
    proxy: str | None = None

    customHeaders: Dict[str, str] = {}

    # anonymousUserID is an important component of telemetry events that get
    # recorded. It is currently optional for backwards compatibility, but
    # it is strongly recommended to set this when connecting to Agent.
    anonymousUserID: str | None = None

    autocompleteAdvancedProvider: str | None = None
    autocompleteAdvancedModel: str | None = None
    debug: bool | None = None
    verboseDebug: bool | None = None

    # When passed, the Agent will handle recording events.
    # If not passed, client must send `graphql/logEvent` requests manually.
    # @deprecated This is only used for the legacy logEvent - use `telemetry` instead.
    eventProperties: Dict | None = None

    customConfiguration: Dict | None = None


class ClientCapabilities(BaseModel):
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
    name: str = "cody-agent"
    version: str = "0.0.5b"
    workspaceRootUri: str | None = None

    # @deprecated Use `workspaceRootUri` instead.
    workspaceRootPath: str | None = None

    extensionConfiguration: ExtensionConfiguration | None = None
    capabilities: ClientCapabilities | None = None

    #
    # Optional tracking attributes to inject into telemetry events recorded
    # by the agent.
    #
    # marketingTracking: TelemetryEventMarketingTrackingInput = None

    def __init__(
        self, name="cody-agent", version="0.0.5b", workspaceRootUri="", **data
    ):
        super().__init__(
            name=name, version=version, workspaceRootUri=workspaceRootUri, **data
        )
        self.name = name
        self.version = version
        self.workspaceRootPath = workspaceRootUri


@dataclass
class ModelSpec:
    model_name: str = ""
    model_id: str = ""
    temperature: float = 0.0
    maxTokensToSample: int = 512


class Models(Enum):
    Claude2 = ModelSpec(
        model_name="Claude 2.0",
        model_id="anthropic/claude-2.0",
    )
    Claude2_1 = ModelSpec(
        model_name="Claude 2.1",
        model_id="anthropic/claude-2.1",
    )
    Claude1_2Instant = ModelSpec(
        model_name="Claude Instant",
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
