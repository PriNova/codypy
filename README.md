# codypy 🐍🤖

**This is a WIP (work-in-progress) project** 🚧👷‍♂️


`codypy` is a Python wrapper binding to Cody Agent through establishing a connection to the Cody-Agent server from [Sourcegraph Cody](https://github.com/sourcegraph/cody) using JSON-RPC (Remote Procedure Call) protocol over a TCP/stdio connection. It allows sending and receiving JSON-RPC messages asynchronously. 📨📥

**Note 1: You need to register an account at [Sourcegraph](https://sourcegraph.com/) and create an API key.**

**Note 2: This project is currently in an experimental alpha stage. The API and functionality may change and break in future versions.** ⚠️🔧



## Features

- Connects to a server using TCP sockets or via stdio
- Sends JSON-RPC messages to the server
- Receives and processes JSON-RPC messages from the server
- Handles connection errors and timeouts
- Extracts method and result from JSON-RPC responses
- Supports asynchronous communication using `asyncio` library
- Show inferred context files if any with optional line ranges

## Requirements

- Python 3.7+
- `asyncio` library
- The Cody Agent CLI binary will be downloaded automatically based on the OS and architecture from https://github.com/sourcegraph/cody/releases

## Installation
### Linux

1. Clone the repository:
   ```
   git clone https://github.com/PriNova/codypy.git
   ```

1. Navigate to the project directory:
   ```
   cd codypy
   ```

1. Ensure you have Python 3.7 or higher installed:
   ```
   python --version
   ```

1. The `asyncio` library is included in the Python standard library, so no additional installation is required.

1. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate
   ```

1. Install the dependencies from the `requirements.txt` file:
   ```
   pip install -r requirements.txt
   ```

1. Rename the provided `env.example` file to `.env` and set the `SRC_ACCESS_TOKEN` value to your API key and the path `BINARY_PATH` to where the cody agent binary should be downloaded and accessed. Use the following command in Linux to rename your file: 
   ```
   mv env.example .env
   ```

1. Run the script using `python main.py`.

You are now ready to use codypy!

**You can also install the package in dev mode via `pip install -e .`**

## Usage as a library

1. Required to set the 'BINARY_PATH' where to download or use the agent binary 
1. Required to set the 'SRC_ACCESS_TOKEN' env to the API Token from your Sourcegraph account.
1. Set your workspace path in the 'workspaceRootUri' property to your local GitHub repository.
1. Run the example script using `python main.py`.
1. The script will attempt to connect to the Cody Agent.
1. If the connection is successful, it will send an initialization message to the server.
1. The script will then receive and process JSON-RPC messages from the server.
1. It will extract and display the method and result from the received messages if `is_debugging` is set to `True`.
1. You will be in 'chat' mode, where you can have a conversation with the Cody Agent based on your input and enhanced context about your codebase.
1. The script will continue to receive messages until you input `/quit`. The server closes then the connection.

## Usage as CLI tool

If installed as a package like mentioned above, you can also use codypy as a CLI tool. Simply export `SRC_ACCESS_TOKEN` and `BINARY_PATH` to your environment and in the terminal execute `codypy-cli --help` to see the available options and flags.

## Example

For an example of initializing and chatting, look at [main.py](https://github.com/PriNova/codypy/blob/main/main.py) file

This example demonstrates how to use a complete cycle to establish a connection to the server and process JSON-RPC messages.

## Roadmap

- [x] Improve the parsing and handling of JSON-RPC responses in `receive_jsonrpc_messages()` function.
- [x] Enhance the initialization message in `initializing_message()` function to include additional client information.
- [x] Implement reliable logging functionality to track client-server communication.
- [x] Implement CLI tooling.
- [x] Download the cody agent binary based on OS and arch.
- [ ] Develop unit tests for key functions in `codypy`.
- [x] Create documentation and examples for using the `codypy` client library.
- [ ] Implement support for including additional context about files and folders.
- [x] Configure repository context.
- [x] Show inferred context files from the conversation.


## License

Copyright notices for third-party code included are licensed under their respective licenses.

This project is licensed under the [MIT License](LICENSE).
