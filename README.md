# Math Driver Gateway

This project implements:
1. **Chardev** kernel module for basic math operations.
2. **Server**: gateway between the chardev and client.
3. **Client**: provides terminal UI for the user and interacts with the server.

## 1. Key features
### 1.1 Chardev
- Accepts two operands and an operator.
- Supports basic math operations  [+,-.*,/].
- Calculates and returns to user space.

### 1.2 Server
- Handle multiple client connections.
- Handle math operations.
- Uses custom protocol with acknowledgment, error types and CRC check.

### 1.3 Client
- Provides basic terminal UI for math operations
- Interacts with the server with the custom protocol.

## 2. Project structure explained
``` console
.
├── build                        # Created by the make/build commands to store artifacts
│
├── ipc                          # Folder for Python Client, Server and C client
│   ├── c_client
│   │   ├── main.c               # C client, main logic
│   │   ├── Makefile
│   │   ├── protocol.c           # Functions for message processing
│   │   └── protocol.h
│   ├── common                   # Share between ipc/py_client/client.py and ipc/server/server.py
│   │   ├── __init__.py
│   │   └── protocol.py          # Functions for message processing
│   ├── protocol.md              # Docs for the protocol structure and flow
│   ├── py_client
│   │   ├── client.py            # Python client entry point, main logic
│   │   └── __init__.py
│   └── server                  
│       ├── device_manager.py    # Class for handling the device driver
│       ├── __init__.py
│       └── server.py            # Server entry point, main logic
├── kernel_module
│   ├── Makefile
│   ├── scripts
│   │   ├── build.sh             # Used for module unloading, building, and calling the loading script
│   │   └── load_chardev.sh      # Loads the chardev
│   └── src
│       └── math_chardev.c       # Kernel module source
├── README.md                  
└── test
    ├── math_chardev
    │   └── test_math_chardev.py # Unit test for the chardev 
    └── py_client_server
        ├── mock_data            # Folder with mock data for multiple clients test
        │   ├── test1_input.txt
        │   ├── test2_input.txt
        │   └── test3_input.txt
        └── test_multiple_clients.sh # Script which creates multiple clients with the mock data and logs into files
```

## 3. Setup instructions

### 3.1 Prerequisites
> Recommended python3 version >=3.10
> Recommended kernel version>=5.x


### 3.2 Download the repo
```console
git clone https://github.com/simeon-s/math-driver-gateway.git && cd math-driver-gateway
```

## **DISCLAIMER**: All commands are designed to be executed from the root project directory!

### 3.3 Build and run kernel module
To build the chardev run this script as sudo:
```console
sudo kernel_module/scripts/build.sh
```
The script will:
- Unload and remove the chardev if it is already present
- Build it
- Load the driver and create a device file

### 3.4 Build C client
### Important! The C client is NOT finished. Error handling and input validation must be adjusted!
**Requires:** `libz.so.1`

To ensure its presence run:
```console
sudo apt-get install zlib1g-dev
```
Build it
```console
sudo make -C ipc/c_client/
```

## 5. Run

### 5.1 Run the kernel module
The `math_chardev` should be already prepared by the ``build.sh`` and ready for usage.
To track the device char messages:
```console
sudo dmesg | grep math_chardev
```

### 5.2 Run the server:
```console
python3 -m ipc.server.server
```

Expected output:

```text
2024-03-27 01:18:17,142 | INFO  | MainThread | Server is listening...
```

### 5.3 Run the Python client in another tab:
```console
cd <project-root-dir>
```

```console
$ python3 -m ipc.py_client.client
```
Expected UI:
```text
(1) Add two numbers
(2) Subtract two numbers
(3) Divide two numbers
(4) Multiply two numbers
(5) Exit
Enter command (1-5):  
```

#### 5.4 Run the C client
```console
build/c_client/main
```
The experience should be similar to the Python one, but it's not finished. The error handling and input validation is not complete.

## 6. Automated tests
### 6.1 Math chardev unit test
The server **should not be working** with active connections, otherwise the device will be busy.
To run a unit test of the kernel module run
``` console
pytest test/math_chardev/test_math_chardev.py
```

### 6.2 Test the server with multiple Python client connections
### 6.2.1 Start the server.
``` console
python3 -m ipc.server.server
```

### 6.2.2 Start the script
It will create multiple clients. Wait for its end.
``` console
test/py_client_server/test_multiple_clients.sh
```

### 6.2.3 Result and logs:
``` console
test/py_client_server/output/
```

## 7. Other
**Environment:** Developed and tested on kernel 6.2.0-37 and Python 3.10.12.

**Tools used:** *ClangFormat* and *Black* for code formatting. 
