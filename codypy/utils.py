import os
import platform
from typing import Any
import tarfile

import aiofiles
import aiohttp

from codypy.config import Configs
from codypy.messaging import request_response


async def _get_platform_arch() -> str | None:
    """
    Recognizes the operating system and architecture of the current system.

    Returns:
        str | None: A string representing the platform and architecture, or None if the platform/architecture could not be determined.
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if machine == "x86_64":
            return "linux_x64"
        elif machine == "aarch64":
            return "linux_arm64"
    elif system == "darwin":
        if machine == "x86_64":
            return "macos_x64"
        elif machine == "arm64":
            return "macos_arm64"
    elif system == "windows":
        if machine == "x64":
            return "win_x64"

    return None


async def _format_arch(arch: str) -> str:
    """
    Formats the platform architecture string to a more human-readable format.

    Args:
        arch (str): The platform architecture string to format.

    Returns:
        str: The formatted platform architecture string.
    """
    if arch == "linux_x64":
        return "linux-x64"
    if arch == "linux_arm64":
        return "linux-arm64"
    if arch == "macos_x64":
        return "macos-x64"
    if arch == "macos_arm64":
        return "macos-arm64"
    if arch == "win_x64":
        return "win-x64"


async def _has_file(binary_path: str, cody_agent_bin: str) -> bool:
    """
    Checks if a file exists at the specified binary path and file name.

    Args:
        binary_path (str): The path to the directory containing the file.
        cody_agent_bin (str): The name of the file to check.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    joined_path_and_file = os.path.join(binary_path, cody_agent_bin)
    return os.path.isfile(joined_path_and_file)


async def _check_for_binary_file(
    binary_path: str, cody_name: str, version: str
) -> bool:
    """
    Checks if a binary file for the Cody agent exists at the specified path.

    Args:
        binary_path (str): The path to the directory containing the Cody agent binary.
        cody_name (str): The name of the Cody agent.
        version (str): The version of the Cody agent.

    Returns:
        bool: True if the Cody agent binary file exists, False otherwise.
    """
    cody_agent = await _format_binary_name(cody_name, version)
    return await _has_file(binary_path, cody_agent)


async def _format_binary_name(cody_name: str, version: str) -> str:
    """
    Formats the name of the Cody agent binary file.

    Args:
        cody_name (str): The name of the Cody agent.
        version (str): The version of the Cody agent.

    Returns:
        str: The formatted name of the Cody agent binary file.
    """
    arch = await _get_platform_arch()
    formatted_arch = await _format_arch(arch)
    return (
        f"{cody_name}-{formatted_arch}-{version}{'.exe' if arch == 'win-x64' else ''}"
    )


async def _download_binary_to_path(
    binary_dir: str, cody_name: str, version: str
) -> bool:
    """
    Downloads a binary file from a GitHub release to the specified path.

    Args:
        binary_path (str): The path to the directory where the binary file should be downloaded.
        cody_name (str): The name of the binary file to download.
        version (str): The version of the binary file to download.

    Returns:
        None
    """
    cody_agent = await _format_binary_name(cody_name, version)
    cody_tar_path = os.path.join(binary_dir, f"{cody_agent}.tar.gz")
    os.makedirs(binary_dir, exist_ok=True)
    cody_binary_path = os.path.join(binary_dir, cody_agent)

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://registry.npmjs.org/@sourcegraph/cody/-/cody-{version}.tgz"
        ) as response:
            if response.status != 200:
                print(f"HTTP error occurred: {response.status}")
                return False

            try:
                async with aiofiles.open(cody_tar_path, "wb") as f:
                    content = await response.read()
                    await f.write(content)
                    print(f"Downloaded {cody_agent} to {binary_dir}")
            except Exception as err:
                print(f"Error occurred while writing the file: {err}")
                return False

    try:
        with tarfile.open(cody_tar_path, "r:gz") as tar:
            tar.extractall(path=binary_dir)
        print(f"Extracted {cody_agent} to {binary_dir}")
        
        # Remove the downloaded tar file
        os.remove(cody_tar_path)
        print(f"Removed temporary file {cody_tar_path}")
        
    except Exception as err:
        print(f"Error occurred while extracting the file: {err}")
        return False
    
    # Create a script that runs `node package/dist/index.js`
    index_js = os.path.join(binary_dir, "package", "dist", "index.js")
    script_content = f'#!/bin/sh\nnode {index_js} "$@"' if os.name != 'nt' else f'@echo off\nnode {index_js} %*'
    
    try:
        with open(cody_binary_path, 'w') as f:
            f.write(script_content)
        
        # Make the script executable on Unix-like systems
        if os.name != 'nt':
            os.chmod(cody_binary_path, 0o755)
        
        print(f"Created executable script at {cody_binary_path}")
    except Exception as err:
        print(f"Error occurred while creating the script: {err}")
        return False



async def get_remote_repositories(
    reader,
    writer,
    id: str,
    configs: Configs,
) -> Any:
    return await request_response("chat/remoteRepos", id, reader, writer, configs)


async def receive_webviewmessage(reader, writer, params, configs: Configs) -> Any:
    return await request_response(
        "webview/receiveMessage",
        params,
        reader,
        writer,
        configs,
    )
