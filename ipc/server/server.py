import socket
import os
import threading
import signal
import struct
import logging
from ipc.common.protocol import Protocol, Message
from ipc.server.device_manager import DeviceManager

# Server configuration
SOCKET_NAME = "/tmp/math_chardev.socket"
DEVICE_PATH = "/dev/math_chardev"
MAX_QUEDUED_CONNS = 5
CLIENT_TIMEOUT = 1800  # seconds

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-5s | %(threadName)s | %(message)s",
)


class Server:
    def __init__(self, socket_path):
        self.socket_path = socket_path
        self.active_connections = 0  # Track the number of active clients
        self.device_lock = (
            threading.Lock()
        )  # To ensure 1 client thread at the time can access the driver
        self.DevManager = DeviceManager(DEVICE_PATH)
        self.is_shutting_down = False  #
        self.setup_socket()

    def setup_socket(self):
        """Setup socket for communication"""
        if os.path.exists(self.socket_path):
            logging.debug("Removing existing socket!")
            try:
                os.unlink(self.socket_path)
                logging.debug("The existing socket was successfully removed")
            except Exception as e:
                raise Exception("Couldn't unlink existing socket!")

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(MAX_QUEDUED_CONNS)
        logging.info("Server is listening...")

    def handle_client(self, conn: socket.socket):
        """Handle an individual client connection."""
        with self.device_lock:
            self.active_connections += 1

        logging.info("Client connected")
        self.send_service_announcement(conn)
        self.DevManager.open_device()

        try:
            while True:
                message = self.receive_message(conn)
                if message is None:
                    break

                logging.info(f"Processing request: {message.payload}")
                with self.device_lock:
                    if self.process_client_request(conn, message):
                        self.transmit_data_response(conn)

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
        finally:
            self.cleanup_connection(conn)

    def receive_message(self, conn: socket.socket):
        """Receive a complete message from the client."""
        try:
            header_data = conn.recv(Protocol.HEADER_SIZE)
            if not header_data:
                logging.info("Client disconnected.")
                return None

            if len(header_data) < Protocol.HEADER_SIZE:
                logging.error("Incomplete header received.")
                return None

            _, length = struct.unpack(Protocol.HEADER_FORMAT, header_data)
            remaining_data = conn.recv(length)

            if len(remaining_data) < length:
                logging.error("Incomplete message received")
                return None

            return Protocol.unpack_message(header_data + remaining_data)
        except socket.error as e:
            logging.error(f"Socket error: {e}")
            return None

    def cleanup_connection(self, conn: socket.socket):
        """
        Cleanup actions when a client connection is terminated.

        Args:
            conn (socket.socket): The client connection socket that is being closed.
        """
        with self.device_lock:
            self.active_connections -= 1
            if self.active_connections == 0:
                logging.info("No active connections, closing the chardev.")
                self.DevManager.close_device()
        conn.close()

    def send_service_announcement(self, conn: socket.socket) -> None:
        """Sends a service announcement message over the given connection."""
        service_message = Protocol.create_service_announcement()
        packed_service_message = Protocol.pack_message(service_message)
        self.send_msg(conn, packed_service_message)

    def process_client_request(self, conn: socket.socket, message: Message) -> bool:
        """
        Processes a client request, writing data to the device and handling responses.

        Args:
            conn (socket.socket): The client connection socket.
            message (Message): The message from the client.

        Returns:
            bool: True if the request was successfully processed, otherwise False
        """
        if message.is_valid_crc():
            write_result = self.DevManager.write_to_device(message.payload)
            self.transmit_ack(conn)
            # Transmit data range error
            if write_result != 0:
                self.transmit_error(conn, write_result)
                return False
            return True
        else:
            self.transmit_error(conn)
            return False

    def send_msg(self, conn: socket.socket, message: bytes) -> bool:
        """
        Sends a message to the client.

        Args:
            conn (socket.socket): The client connection socket.
            message (bytes): The message to be sent.

        Returns:
            bool: True if the message was successfully sent, otherwise False
        """
        try:
            logging.debug(f"send_msg(): {message}")
            conn.sendall(message)
            return True
        except Exception as e:
            logging.error(f"Error sending message: {message}\nException: {e}")
            return False

    def transmit_ack(self, conn: socket.socket) -> bool:
        """Sends an acknowledgment (ACK) message to the client"""
        ack_message = Protocol.pack_message(Message(Protocol.ACK_T, ""))
        success = self.send_msg(conn, ack_message)

        if success:
            logging.debug("Sent ACK")
        else:
            logging.error("Failed sending ACK!")

        return success

    def transmit_error(self, conn, error_code=Protocol.ERROR_T, error_message=""):
        """
        Transmits an error message to the client.

        Args:
            conn (socket): The client connection socket.
            error_code (int): The error code to transmit. Defaults to Protocol.ERROR_T.
            error_message (str): Additional error message for descriptive errors.
        """
        error_payload = f"{error_code}:{error_message}"
        error_msg = Protocol.pack_message(Message(error_code, error_payload))
        if self.send_msg(conn, error_msg):
            logging.info(f"Sent ERROR type {error_code} with message: {error_message}")
        else:
            logging.error(f"Failed to send ERROR type {error_code}")

    def transmit_data_response(self, conn):
        """Sends a data response to the client"""
        data = self.DevManager.read_from_device()
        if data is None:
            logging.error("Failed to read data from device.")
            self.transmit_error(
                conn, error_code=Protocol.ERROR_T, error_message="Read failure"
            )
            return

        logging.info(f"Sending result: {data}")
        data_message = Protocol.pack_message(Message(Protocol.DATA_T, data))

        if not self.send_msg(conn, data_message):
            logging.error("Failed sending DATA!")
            self.transmit_error(
                conn, error_code=Protocol.ERROR_T, error_message="Send failure"
            )

    def shutdown_server(self):
        """Gracefully shuts down the server."""
        if self.is_shutting_down:
            return
        self.is_shutting_down = True
        logging.info("Shutting down the server...")
        with self.device_lock:
            if self.active_connections > 0:
                self.DevManager.close_device()
        self.server_socket.close()

    def signal_handler(self, signum, frame):
        """Handles received system signals and initiates server shutdown."""
        logging.info(f"Signal {signum} received, shutting down...")
        self.shutdown_server()
        exit(0)

    def run(self):
        """Starts the server and handles incoming connections."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        try:
            # Main loop for handling connections
            while not self.is_shutting_down:
                if self.is_shutting_down:
                    logging.info(
                        "Server is shutting down, terminating client handling."
                    )
                    break
                conn, _ = self.server_socket.accept()
                conn.settimeout(CLIENT_TIMEOUT)
                client_thread = threading.Thread(
                    target=self.handle_client, args=(conn,)
                )
                client_thread.start()
        finally:
            logging.info("Closing server.")
            self.shutdown_server()  # TODO connection hangs out


if __name__ == "__main__":
    server = Server(SOCKET_NAME)
    server.run()
