# CodyAgentPy 🐍🤖

**This is a WIP (work-in-progress) project** 🚧👷‍♂️

CodyAgentPy is a Python wrapper binding to Cody Agent through establishing a connection to the Cody-Agent server from [Sourcegraph Cody](https://github.com/sourcegraph/cody) using JSON-RPC (Remote Procedure Call) protocol over a TCP/stdio connection. It allows sending and receiving JSON-RPC messages asynchronously. 📨📥

**Note 1: You need to register an account at [Sourcegraph](https://sourcegraph.com/) and create an API key.**

**Note 2: This project is currently in an experimental alpha stage. The API and functionality may change and break in future versions.** ⚠️🔧



## Features

- Connects to a server using TCP sockets
- Sends JSON-RPC messages to the server
- Receives and processes JSON-RPC messages from the server
- Handles connection errors and timeouts
- Extracts method and result from JSON-RPC responses
- Supports asynchronous communication using `asyncio` library

## Requirements

- Python 3.7+
- `asyncio` library

## Installation
### Linux

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/CodyAgentPy.git
   ```

2. Navigate to the project directory:
   ```
   cd CodyAgentPy
   ```

3. Ensure you have Python 3.7 or higher installed:
   ```
   python --version
   ```

4. The `asyncio` library is included in the Python standard library, so no additional installation is required.

5. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate
   ```

6. Install the dependencies from the `requirements.txt` file:
   ```
   pip install -r requirements.txt
   ```
7. Run the script using `python CodyAgentPy.py`.

**Note**: Currently you need to set the path to the agent binary or the built script in the sourcegraph/cody/agent repository



You are now ready to use CodyAgentPy!


## Usage

1. You need to retreivve the 'Config' class with 'get_configs()'.
1. Set at least the 'BINARY_PATH' property to the agent binary or the build 'index.js' file.
1. Run the example script using `python main.py`.
1. The script will attempt to connect to the Cody Agent.
1. If the connection is successful, it will send an initialization message to the server.
1. The script will then receive and process JSON-RPC messages from the server.
1. It will extract and display the method and result from the received messages.
1. The script will continue to receive messages until the server closes the connection or a timeout occurs.

## Example

For an example of initializing and send two chat messages, look at [main.py](https://github.com/PriNova/CodyAgentPy/blob/main/main.py) file

This example demonstrates how to use a complete cycle to establish a connection to the server and process JSON-RPC messages.

## Roadmap

- [ x ] Improve the parsing and handling of JSON-RPC responses in `receive_jsonrpc_messages()` function.
- [ x ] Enhance the initialization message in `initializing_message()` function to include additional client information.
- [ ] Implement logging functionality to track client-server communication.
- [ x ] Add configuration options for server address, port, and other settings.
- [ ] Develop unit tests for key functions in `CodyAgentPy.py`.
- [ ] Create documentation and examples for using the `CodyAgentPy` client library.


## License

Copyright notices for third-party code included are licensed under their respective licenses.

This project is licensed under the [MIT License](LICENSE).
