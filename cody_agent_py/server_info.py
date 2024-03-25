from pydantic import BaseModel

class CodyLLMSiteConfiguration(BaseModel):
    chatModel: str = None
    chatModelMaxTokens: int = None
    fastChatModel: str = None
    fastChatModelMaxTokens: int = None
    completionModel: str = None
    completionModelMaxTokens: int = None
    provider: str = None

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
    displayName: str = None
    avatarURL: str
    configOverwrites: CodyLLMSiteConfiguration = None


class ServerInfo(BaseModel):
    name: str
    authenticated: bool = None
    cody_enabled: bool = None
    cody_version: str = None
    authStatus: AuthStatus = None
