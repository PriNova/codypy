from typing import Literal, Optional

from pydantic import BaseModel


class ExtensionConfiguration(BaseModel):
    accessToken: str = ''
    serverEndpoint: str = "https://sourcegraph.com"
    codebase: str = None
    proxy: str = None
    
    customHeaders: dict[str, str] = {}

    # anonymousUserID is an important component of telemetry events that get
    # recorded. It is currently optional for backwards compatibility, but
    # it is strongly recommended to set this when connecting to Agent.
    anonymousUserID: str = None

    autocompleteAdvancedProvider: str = None
    autocompleteAdvancedModel: str = None
    debug: bool = None
    verboseDebug: bool = None
    

    # When passed, the Agent will handle recording events.
    # If not passed, client must send `graphql/logEvent` requests manually.
    # @deprecated This is only used for the legacy logEvent - use `telemetry` instead.
    eventProperties: dict = None

    customConfiguration: dict = None


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


class ClientInfo(BaseModel):
    name: str = 'defaultClient'
    version: str = "v1"
    workspaceRootUri: str

    # @deprecated Use `workspaceRootUri` instead.
    workspaceRootPath: str = None

    extensionConfiguration: ExtensionConfiguration = None
    capabilities: ClientCapabilities = None

    #
    # Optional tracking attributes to inject into telemetry events recorded
    # by the agent.
    #
    #marketingTracking: TelemetryEventMarketingTrackingInput = None

    def __init__(self, name = 'defaultClient', version = "v1", workspaceRootUri = '', **data):
        super().__init__(
            name=name, version=version, workspaceRootUri=workspaceRootUri, **data
        )
        self.name = name
        self.version = version
        self.workspaceRootPath = workspaceRootUri

