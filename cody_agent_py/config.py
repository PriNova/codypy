from dataclasses import dataclass

@dataclass
class Config:
    BINARY_PATH: str
    SERVER_ADDRESS = ('localhost', 3113)
    WORKSPACE: str = ''
    USE_BINARY: bool = False
    USE_TCP: bool = False
    IS_DEBUGGING: bool = True