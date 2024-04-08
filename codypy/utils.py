import asyncio
import os
import platform

import requests


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


async def check_for_binary_file(binary_path: str, cody_name: str, version: str) -> bool:
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
    has_bin = await _has_file(binary_path, cody_agent)
    return has_bin


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


async def download_binary_to_path(
    binary_path: str, cody_name: str, version: str
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
    cody_binaray_path = os.path.join(binary_path, cody_agent)

    r = requests.get(
        f"https://github.com/sourcegraph/cody/releases/download/agent-v{version}/{cody_agent}"
    )
    try:
        r.raise_for_status()
        with open(cody_binaray_path, "wb") as f:
            f.write(r.content)
            print(f"Downloaded {cody_agent} to {binary_path}")
            
            # set permission to chmod +x for the downloaded file
            os.chmod(cody_binaray_path, 0o755)
            return True
    except requests.exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
        return False
    except requests.exceptions.ConnectionError as err:
        print(f"Error connecting to server: {err}")
        return False


async def main():
    binary = await check_for_binary_file(
        "/home/prinvoa/CodeProjects/CodyAgentPy/bin", "cody-agent", "0.0.5"
    )
    print(binary)


# Usage
asyncio.run(main=main())
