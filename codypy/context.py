import os
from dataclasses import dataclass

from codypy.logger import log_message


@dataclass
class Uri:
    fsPath: str = ""
    path: str = ""


@dataclass
class Context:
    type: str = "file"
    uri: Uri | None = None


context_file_paths: list[Context] = []


def append_paths(*paths: str) -> list[Context]:
    """
    Appends the provided file paths to the `context_file_paths` list, creating a `Context` object for each path.

    Args:
        *paths (str): One or more file paths to append to the `context_file_paths` list.

    Returns:
        list[Context]: The updated `context_file_paths` list.
    """
    for path in paths:
        if not os.path.exists(path):
            log_message("append_paths", f"WARNING: The path {path} does not exist.")

        uri = Uri()
        uri.fsPath = path
        uri.path = path
        context = Context()
        context.uri = uri
        context_file_paths.append(context)

    return context_file_paths
