#include "protocol.h"

// Function to compute CRC32 checksum
unsigned long compute_checksum_crc32(const char *data) {
  return crc32(0L, (const unsigned char *)data, strlen(data));
}

// Function to create a new Message
struct Message create_message(int type, char *payload) {
  struct Message message;
  message.type = type;
  message.payload = strdup(payload);                  // Duplicate the payload
  message.checksum = compute_checksum_crc32(payload); // Compute checksum
  message.length = strlen(payload);
  return message;
}

// Function to pack a Message
char *pack_message(struct Message message) {
  int payload_length = message.length;
  int total_length =
      HEADER_SIZE + (payload_length + 2 * PADDING_SIZE) + CHECKSUM_SIZE;

  char *packed_message = malloc(total_length);

  // Pack the header
  packed_message[0] = (char)message.type;
  *((int *)(packed_message + 1)) =
      htonl(payload_length + 2 * PADDING_SIZE + CHECKSUM_SIZE);

  // Add padding and payload
  packed_message[HEADER_SIZE] = PADDING_BYTE;
  memcpy(packed_message + PAYLOAD_OFFSET, message.payload, payload_length);
  packed_message[PAYLOAD_OFFSET + payload_length] = PADDING_BYTE;

  // Pack checksum at the correct offset
  unsigned long net_checksum =
      htonl(message.checksum); // Convert to network byte order
  memcpy(packed_message + CHECKSUM_OFFSET(payload_length), &net_checksum,
         CHECKSUM_SIZE);

  return packed_message;
}

// Function to unpack a Message
struct Message unpack_message(char *packed_message) {
  struct Message message;

  // Unpack the header
  message.type = (int)packed_message[0];
  int total_length = ntohl(*((int *)(packed_message + 1)));
  int payload_length = total_length - 2 * PADDING_SIZE - CHECKSUM_SIZE;

  // Extract the payload
  message.payload = malloc(payload_length + 1);
  memset(message.payload, 0, payload_length + 1);
  memcpy(message.payload, packed_message + PAYLOAD_OFFSET, payload_length);
  message.payload[payload_length] = '\0'; // Null-terminate the string
  message.length = payload_length;

  // Extract and set the checksum
  message.checksum = ntohl(
      *((unsigned long *)(packed_message + CHECKSUM_OFFSET(payload_length))));

  return message;
}
