from pydantic import BaseModel


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