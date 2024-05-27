class CodyPyError(Exception):
    """Base class for all CodyPy exceptions."""

    pass


class AgentAuthenticationError(CodyPyError):
    """Exception raised for errors in the authentication of the Cody agent."""

    def __init__(self, message="Agent authentication failed"):
        self.message = message
        super().__init__(self.message)


class AgentBinaryDownloadError(CodyPyError):
    """Raised when there is an error downloading the Cody Agent binary."""

    def __init__(self, message="Failed to download the Cody Agent binary"):
        self.message = message
        super().__init__(self.message)


class AgentBinaryNotFoundError(CodyPyError):
    """Raised when the Cody Agent binary is not found."""

    def __init__(self, message="Cody Agent binary not found"):
        self.message = message
        super().__init__(self.message)


class ServerTCPConnectionError(CodyPyError):
    """Raised when there is an error connecting to the server via TCP."""

    def __init__(self, message="Could not connect to server via TCP"):
        self.message = message
        super().__init__(self.message)
