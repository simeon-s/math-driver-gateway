#!/usr/bin/env python3

import socket
import time
import logging
import struct
from ipc.common.protocol import Protocol, Message
import sys
from typing import Optional

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s | %(levelname)-5s | %(message)s"
)

SOCKET_NAME = "/tmp/math_chardev.socket"
RETRY_LIMIT = 3
RETRY_DELAY = 5  # seconds
MAX_PAYLOAD_SIZE = 1024
ERROR_MESSAGES = {
    3: "Generic error message!",
    22: "Generic error message!",  # EINVAL
    34: "Result is too large",  # ERANGE
    75: "Overflow or underflow error",  # EOVERFLOW
}


class Client:
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.client_socket = None
        self.is_connected = self.connect_to_server()
        self.last_received_data = None

    def connect_to_server(self):
        for attempt in range(RETRY_LIMIT):
            try:
                self.client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                logging.debug(f"Connecting to server at {self.socket_path}")
                self.client_socket.connect(self.socket_path)
                self.client_socket.settimeout(None)

                # Wait for the service announcement message
                if self.wait_for_service_announcement():
                    logging.debug("Service announcement received.")
                else:
                    logging.error("Failed to receive service announcement.")
                    return False

                return True
            except socket.error as e:
                logging.error(f"Socket error: {e}")
                if attempt < RETRY_LIMIT - 1:
                    logging.info("Failed to connect. Retrying...")
                    time.sleep(RETRY_DELAY)
        logging.error("Failed to communicate with the server after several attempts.")
        return False

    def wait_for_service_announcement(self) -> bool:
        """Wait for the server's service announcement and return True if received."""
        received_data_type = self.process_message()
        return received_data_type == Protocol.SERVICE_ANNOUNC_T

    def send_and_receive(self, data_to_send: str) -> Optional[bool]:
        """Send data to the server and return the result of the operation."""
        if not self.is_connected:
            logging.error("Not connected to the server.")
            return None

        if not self.send_msg(data_to_send):
            return None

        if not self.receive_ack():
            return None

        return self.receive_result()

    def send_msg(self, data: str) -> bool:
        """Send a message to the server and return True if the operation is successful."""
        message = Message(Protocol.DATA_T, data)
        data_message = Protocol.pack_message(message)

        try:
            self.client_socket.sendall(data_message)
            return True
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            return False

    def send_msg(self, data):
        message = Message(Protocol.DATA_T, data)
        data_message = Protocol.pack_message(message)

        try:
            self.client_socket.sendall(data_message)
            return True
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            return False

    def receive_ack(self) -> bool:
        """Wait for an acknowledgment from the server and return True if received."""
        received_data_type = self.process_message()
        if received_data_type == Protocol.ACK_T:
            logging.info("Request OKAY...")
            return True
        logging.error("Problem the request, ACK not received!")
        return False

    def receive_result(self) -> bool:
        """Receive the result from the server, handle errors, and return if successful return True."""
        logging.info("Receiving response...")
        received_data_type = self.process_message()
        if received_data_type == Protocol.DATA_T:
            logging.info(f"Result received: {self.last_received_data}")
            print(f"Result received: {self.last_received_data}")
            return True
        elif received_data_type in ERROR_MESSAGES:
            error_message = ERROR_MESSAGES[received_data_type]
            logging.error("Error message received.")
            logging.error(f"Error message code: {received_data_type}")
            logging.error(error_message)
            return False
        else:
            logging.error("Result not received.")
            return False

    def process_message(self) -> Optional[int]:
        """
        Wait for a message from the server, unpack it, and process it according to its type.
        Returns the message type, or None if no complete message is received.
        """
        buffer_size = Protocol.HEADER_SIZE + MAX_PAYLOAD_SIZE + Protocol.CRC_SIZE
        data = self.client_socket.recv(buffer_size)

        # Check if the header is complete
        if len(data) < Protocol.HEADER_SIZE:
            logging.debug("Incomplete header received")
            return None

        while len(data) >= Protocol.HEADER_SIZE:
            # Extract the header and determine the length of the message
            header_data = data[: Protocol.HEADER_SIZE]
            _, length = struct.unpack(Protocol.HEADER_FORMAT, header_data)

            # Check if the entire message is received
            if len(data) < Protocol.HEADER_SIZE + length:
                logging.debug("Incomplete message received")
                break

            # Isolate the complete message and prepare the buffer for the next message
            message_data = data[: Protocol.HEADER_SIZE + length]
            data = data[Protocol.HEADER_SIZE + length :]

            # Unpack and process the message
            received_message = Protocol.unpack_message(message_data)

            # Handle the message according to its type
            if received_message.type == Protocol.DATA_T:
                self.last_received_data = received_message.payload
            elif received_message.type == Protocol.SERVICE_ANNOUNC_T:
                logging.debug(f"Service announcement: {received_message.payload}")

            # Return the message type
            return received_message.type

        # If no complete message is received
        logging.debug("No complete message received")
        return None

    def received_data(self):
        return self.last_received_data


def read_input_output_list(filename):
    with open(filename, "r") as file:
        return [line.strip().split(",") for line in file]


def run_tests(test_cases_file):
    try:
        client = Client(SOCKET_NAME)
        if not client.is_connected:
            print("Failed to connect to the server.")
            return

        test_cases_list = read_input_output_list(test_cases_file)

        for input_expr, expected_output in test_cases_list:
            logging.info(f"Sending: {input_expr}")
            client.send_and_receive(input_expr)
            received_output = client.received_data()
            if received_output == str(expected_output):
                logging.info(
                    f"Test passed for {input_expr}. Expected: {expected_output}, Received: {received_output}"
                )
            else:
                logging.error(
                    f"Test failed for {input_expr}. Expected: {expected_output}, Received: {received_output}"
                )
            time.sleep(1)
    except FileNotFoundError:
        logging.error("Test cases file not found.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


def run_cli():
    try:
        client = Client(SOCKET_NAME)
        if not client.is_connected:
            print("Failed to connect to the server.")
            return

        # Enter CLI event loop
        while True:
            print("(1) Add two numbers")
            print("(2) Subtract two numbers")
            print("(3) Divide two numbers")
            print("(4) Multiply two numbers")
            print("(5) Exit")

            choice = input("Enter command (1-5): ")

            if choice == "5":
                print("Exiting the program.")
                break

            if choice not in ["1", "2", "3", "4"]:
                print("Invalid option. Please try again.")
                continue

            while True:
                try:
                    num1 = int(input("Enter operand 1: "))
                    break
                except ValueError:
                    print("Invalid input. Please enter a number.")

            while True:
                try:
                    num2 = int(input("Enter operand 2: "))
                    if choice == "3" and num2 == 0:
                        print("Cannot divide by zero. Please enter a non-zero number.")
                        continue
                    break
                except ValueError:
                    print("Invalid input. Please enter a number.")

            operation = ""
            if choice == "1":
                operation = "+"
            elif choice == "2":
                operation = "-"
            elif choice == "3":
                operation = "/"
            elif choice == "4":
                operation = "*"

            expression = f"{num1}{operation}{num2}"
            print(f"{expression=}")
            client.send_and_receive(expression)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def main():
    args = sys.argv[1:]

    if not args:
        run_cli()
    else:
        # Run tests with file
        test_cases_file = sys.argv[1]
        run_tests(test_cases_file)


if __name__ == "__main__":
    main()
