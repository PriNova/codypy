from dataclasses import dataclass


@dataclass
class Configs:
    BINARY_PATH: str
    SERVER_ADDRESS = ("localhost", 3113)
    WORKSPACE: str = ""
    USE_BINARY: bool = False
    USE_TCP: bool = False
    IS_DEBUGGING: bool = True


configs = Configs("")


async def get_configs() -> Configs:
    return configs
