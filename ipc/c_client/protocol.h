#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

// Define constants
#define DATA_T 0
#define ACK_T 1
#define SERVICE_ANNOUNC_T 2
#define ERROR_T 3
#define ERROR_NO_T 34       // Out of range error
#define ERROR_OVERFLOW_T 75 // Data overflow/underflow

#define ERROR_T_MSG "Generic error message!\n"
#define ERROR_NO_T_MSG "Result is too large\n"
#define ERROR_OVERFLOW_T_MSG "Overflow or underflow error\n"
#define ERROR_UNKNOWN_MSG "Unknown error\n"

#define HEADER_SIZE 5   // Size of Type (1 byte) + Length (4 bytes)
#define CHECKSUM_SIZE 4 // Size of the CRC32 checksum
#define PADDING_BYTE 0xFF
#define PADDING_SIZE 1 // Size of the padding byte

// Additional Constants for offsets
#define PAYLOAD_OFFSET                                                         \
  (HEADER_SIZE + PADDING_SIZE) // Starting index of the payload
#define CHECKSUM_OFFSET(payload_length)                                        \
  (PAYLOAD_OFFSET + (payload_length) +                                         \
   PADDING_SIZE) // Starting index of the checksum

// Define the Message struct
struct Message {
  int type;
  int length; // Length of the payload
  char *payload;
  unsigned long checksum; // 4-byte checksum
};

// Function declarations
unsigned long compute_checksum_crc32(const char *data);
struct Message create_message(int type, char *payload);
char *pack_message(struct Message message);
struct Message unpack_message(char *packed_message);

#endif // PROTOCOL_H
