import os
from datetime import datetime
from logging import DEBUG, FileHandler, Formatter, getLogger

# Create a global logger instance
logger = None


def setup_logger(name, workspace_path):
    """
    Sets up a logger with a file handler for the specified name and workspace path.

    Args:
        name (str): The name of the logger.
        workspace_path (str): The path to the workspace directory.

    Returns:
        Logger: The configured logger instance.
    """
    global logger

    log_dir = os.path.join(workspace_path, name)
    os.makedirs(log_dir, exist_ok=True)

    # Get the current date
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Include the date in the log file name
    log_file = os.path.join(log_dir, f"{current_date}_{name}.log")

    logger = getLogger(name)
    logger.setLevel(DEBUG)

    handler = FileHandler(log_file)
    handler.setLevel(DEBUG)

    formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


def log_message(scope: str, message: str):
    global logger
    logger.debug(f"{scope} {message}")
