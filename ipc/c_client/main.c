#include "protocol.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#define SOCKET_NAME "/tmp/math_chardev.socket"
#define BUFFER_SIZE 128

typedef enum {
  STATE_INIT,
  STATE_CONNECT,
  STATE_RECEIVE_ANNOUNCEMENT,
  STATE_RECEIVE_INPUT,
  STATE_SEND,
  STATE_RECEIVE_ACK,
  STATE_RECEIVE_RESPONSE,
  STATE_CLOSE,
  STATE_DONE,
  STATE_ERROR
} ClientState;

typedef struct {
  int operand1;
  int operand2;
  char operation;
  int is_valid; // Flag to indicate valid input or exit command
} ClientInput;

int create_socket();
void connect_to_server(int socket_fd, struct sockaddr_un *server_address);
void send_message(int socket_fd, unsigned char *message, size_t message_size);
struct Message receive_message(int socket_fd, char *buffer, size_t buffer_size);
ClientInput receive_input(void);
int read_operand(const char *prompt);
const char *getErrorMessage(int errorCode);

int main() {
  struct sockaddr_un server_address;
  int socket_fd;
  char ack_buffer[BUFFER_SIZE];
  char resp_buffer[BUFFER_SIZE];
  char *packed_msg_data;
  size_t packed_msg_size;
  struct Message ack_message, response_message, announce_msg;
  struct Message data_message_struct;
  ClientState state = STATE_INIT;

  while (state != STATE_DONE) {
    switch (state) {
    case STATE_INIT:
      socket_fd = create_socket();
      state = STATE_CONNECT;
      break;

    case STATE_CONNECT:
      connect_to_server(socket_fd, &server_address);
      state = STATE_RECEIVE_ANNOUNCEMENT;
      break;

    case STATE_RECEIVE_ANNOUNCEMENT:
      announce_msg = receive_message(socket_fd, ack_buffer, BUFFER_SIZE);
      if (announce_msg.type != SERVICE_ANNOUNC_T) {
        fprintf(stderr, "Did not receive announce msg, received type: %d\n",
                announce_msg.type);
        state = STATE_ERROR;
      } else {
        // Announcement received
        free(announce_msg.payload);
        state = STATE_RECEIVE_INPUT;
      }
      break;

    case STATE_RECEIVE_INPUT: {
      ClientInput input = receive_input();
      if (!input.is_valid) {
        state = STATE_CLOSE;
      } else {
        char message_buffer[64];
        snprintf(message_buffer, sizeof(message_buffer), "%d%c%d",
                 input.operand1, input.operation, input.operand2);
        data_message_struct = create_message(DATA_T, message_buffer);
        state = STATE_SEND;
      }
    } break;

    case STATE_SEND:
      packed_msg_data = pack_message(data_message_struct);
      packed_msg_size = HEADER_SIZE + 2 * PADDING_SIZE +
                        strlen(data_message_struct.payload) + CHECKSUM_SIZE;
      send_message(socket_fd, (unsigned char *)packed_msg_data,
                   packed_msg_size);
      free(packed_msg_data);
      state = STATE_RECEIVE_ACK;
      break;

    case STATE_RECEIVE_ACK:
      ack_message = receive_message(socket_fd, ack_buffer, BUFFER_SIZE);
      if (ack_message.type != ACK_T) {
        fprintf(stderr, "Did not receive ACK, received type: %d\n",
                ack_message.type);
        state = STATE_ERROR;
      } else {
        printf("Request OKAY...\n");
        free(ack_message.payload);
        state = STATE_RECEIVE_RESPONSE;
      }
      break;

    case STATE_RECEIVE_RESPONSE:
      response_message = receive_message(socket_fd, resp_buffer, BUFFER_SIZE);

      if (response_message.type == ERROR_T ||
          response_message.type == ERROR_NO_T ||
          response_message.type == ERROR_OVERFLOW_T) {
        printf("Received error: %d %s", response_message.type,
               getErrorMessage(response_message.type));
      }

      if (response_message.type == DATA_T) {
        printf("Result is %s!\n", response_message.payload);
      }

      free(response_message.payload);
      state = STATE_RECEIVE_INPUT;
      break;

    case STATE_CLOSE:
      printf("Closing socket...\n");
      close(socket_fd);
      state = STATE_DONE;
      break;

    case STATE_ERROR:
      perror("An error occurred");
      close(socket_fd);
      state = STATE_DONE;
      break;

    default:
      fprintf(stderr, "Invalid state\n");
      exit(EXIT_FAILURE);
    }
  }

  printf("Client terminated successfully.\n");
  return 0;
}

int create_socket() {
  int socket_fd;
  if ((socket_fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1) {
    perror("Socket error");
    exit(EXIT_FAILURE);
  }
  return socket_fd;
}

void connect_to_server(int socket_fd, struct sockaddr_un *server_address) {
  memset(server_address, 0, sizeof(*server_address));
  server_address->sun_family = AF_UNIX;

  size_t length = sizeof(server_address->sun_path) - 1; // Max length, reserve space for null term
  memcpy(server_address->sun_path, SOCKET_NAME, length);
  server_address->sun_path[length] = '\0';

  if (connect(socket_fd, (struct sockaddr *)server_address,
              sizeof(*server_address)) == -1) {
    perror("Connect error");
    exit(EXIT_FAILURE);
  }
}

void send_message(int socket_fd, unsigned char *message, size_t message_size) {
  printf("Sending request...\n");
  if (write(socket_fd, message, message_size) == -1) {
    perror("Write error");
    exit(EXIT_FAILURE);
  }
}

struct Message receive_message(int socket_fd, char *buffer,
                               size_t buffer_size) {
  memset(buffer, 0, buffer_size);
  int length = read(socket_fd, buffer, buffer_size);

  if (length <= 0) {
    perror("Error in reading message!");
    close(socket_fd);
    exit(EXIT_FAILURE);
  }

  return unpack_message(buffer);
}

ClientInput receive_input() {
  ClientInput input = {0, 0, 0, 0};

  while (1) {
    int choice;

    printf("(1) Add two numbers\n");
    printf("(2) Subtract two numbers\n");
    printf("(3) Divide two numbers\n");
    printf("(4) Multiply two numbers\n");
    printf("(5) Exit\n");

    printf("Enter command (1-5): ");
    if (scanf("%d", &choice) != 1) {
      printf("Invalid input. Please enter a number.\n");
      // Clear the input buffer
      while (getchar() != '\n')
        ;
      continue;
    }

    if (choice == 5) {
      printf("Exiting the program.\n");
      input.is_valid = 0; // 0 for exit
      break;
    }

    if (choice < 1 || choice > 4) {
      printf("Invalid option. Please try again.\n");
      continue;
    }

    input.operand1 = read_operand("Enter operand 1: ");
    input.operand2 = read_operand("Enter operand 2: ");

    if (choice == 1) {
      input.operation = '+';
    } else if (choice == 2) {
      input.operation = '-';
    } else if (choice == 3) {
      if (input.operand2 == 0) {
        printf("Cannot divide by zero.\n");
        continue;
      }
      input.operation = '/';
    } else if (choice == 4) {
      input.operation = '*';
    }

    input.is_valid = 1;
    break;
  }

  return input;
}

int read_operand(const char *prompt) {
  int num;
  char term;
  for (;;) {
    printf("%s", prompt);
    if (scanf("%d%c", &num, &term) != 2 || term != '\n') {
      printf("Invalid input. Please enter a number:\n");
      int c;
      while (('\n' != (c = fgetc(stdin))) && (c != EOF))
        ; // clear up to end of line
      if (c == EOF) {
        // Handle EOF if necessary
        return -1; // Or some other value indicating error/EOF
      }
    } else {
      // printf("Valid integer followed by enter key\n");
      break;
    }
  }
  return num;
}

const char *getErrorMessage(int errorCode) {
  switch (errorCode) {
  case ERROR_T:
    return ERROR_T_MSG;
  case ERROR_NO_T:
    return ERROR_NO_T_MSG;
  case ERROR_OVERFLOW_T:
    return ERROR_OVERFLOW_T_MSG;
  default:
    return ERROR_UNKNOWN_MSG;
  }
}
