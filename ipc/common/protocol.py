import struct
import zlib
import logging
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(threadName)s | %(message)s",
)
logger = logging.getLogger(__name__)


class Message:
    def __init__(self, type: int, payload: str, crc: Optional[int] = None) -> None:
        self.type = type
        self.payload = payload
        self.crc = crc or self.compute_crc()

    def compute_crc(self) -> int:
        return zlib.crc32(self.payload.encode()) & 0xFFFFFFFF

    def is_valid_crc(self) -> bool:
        return self.crc == self.compute_crc()


class Protocol:
    # Constants for message structure
    # Header which contains the byte order, type and length of the payload
    HEADER_FORMAT = "!BI"  # (!) - Big Endian, (B) unsigned char, (I) - unsigned int
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    # Message types
    DATA_T = 0
    ACK_T = 1
    SERVICE_ANNOUNC_T = 2
    ERROR_T = 3  # Generic error, unsuccessful command
    ERROR_NO_T = 34  # Out of range error
    ERROR_OVERFLOW_T = 75  # Data overflow/underflow

    # Padding details
    PADDING_BYTE = b"\xFF"  # Padding byte
    PADDING_SIZE = 1  # Size of padding byte
    # Service announcement payload
    SERVICE_ANNOUNCE_PAYLOAD = (
        "Operations: add, subtract, multiply, divide signed integers"
    )
    # Last part of the message
    CRC_SIZE = 4  # Bytes

    @classmethod
    def create_message(cls, type: int, payload: str) -> Message:
        return Message(type, payload)

    @classmethod
    def create_service_announcement(cls) -> Message:
        return cls.create_message(cls.SERVICE_ANNOUNC_T, cls.SERVICE_ANNOUNCE_PAYLOAD)

    @classmethod
    def pack_message(cls, message: Message) -> bytes:
        # Pad the payload with a padding byte at the beginning and end
        payload_with_padding = (
            cls.PADDING_BYTE + message.payload.encode() + cls.PADDING_BYTE
        )
        logger.debug(f"{payload_with_padding=}| {len(payload_with_padding)}")

        # Calculate the total length of the payload including padding and CRC
        payload_length = len(payload_with_padding) + cls.CRC_SIZE
        # Pack the header with message type and total payload length
        header = struct.pack(cls.HEADER_FORMAT, message.type, payload_length)
        # Pack the CRC value
        crc = struct.pack("!I", message.crc)

        # Combine header, padded payload, and CRC into one byte seq
        return header + payload_with_padding + crc

    @classmethod
    def unpack_message(cls, message_data: bytes) -> Message:
        # Extract the header from the message data
        header = message_data[: cls.HEADER_SIZE]
        # Unpack the header to get type and length
        type, length = struct.unpack(cls.HEADER_FORMAT, header)
        # Extract the payload and CRC, based on the calculated length
        payload_and_crc = message_data[cls.HEADER_SIZE : length + cls.HEADER_SIZE]
        # Remove padding from the payload
        payload = payload_and_crc[cls.PADDING_SIZE : -cls.CRC_SIZE - cls.PADDING_SIZE]
        # Extract the CRC value
        crc = payload_and_crc[-cls.CRC_SIZE :]
        unpacked_crc = struct.unpack("!I", crc)[0]

        # Return the unpacked message
        return Message(type, payload.decode(), unpacked_crc)


# Usage example
service_message = Protocol.create_service_announcement()
packed_service_message = Protocol.pack_message(service_message)
logger.debug(f"Packed Service Message: {packed_service_message}")
hex_representation = " ".join(f"{byte:02x}" for byte in packed_service_message)
logger.debug(f"Packed Service Message (Hex): {hex_representation}")

unpacked_service_message = Protocol.unpack_message(packed_service_message)
logger.debug(f"Unpacked Service Message: {unpacked_service_message.payload}")
