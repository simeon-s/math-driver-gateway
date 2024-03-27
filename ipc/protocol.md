### Message Structure
A message of the protocol contains three main parts: **Header**, **Payload**, and **CRC**.

#### Header
- **Type**: 1 byte (0 for DATA, 1 for ACK, or other for ERROR)
- **ID**: 4 bytes (Unique identifier for each message)
- **Length**: 4 bytes (Length of the Payload in bytes)

#### Payload
- The actual data being transmitted.

#### CRC
- CRC of the Payload.
- Length: 4 bytes

### Message Types
#### DATA (Type 0)
- Used for sending data from the client to the server.

#### ACK (Type 1)
- Sent by the server to acknowledge the successful receipt of a DATA message.

#### SERVICE ANNOUNCEMENT (Type 2)
- Sent by the server to announce the available operations on connect.

#### ERROR (Type 3 or other[34,75...])
- Sent by the server if there's an error (e.g. overflow, CRC mismatch) in the DATA message.

### Communication Flow
1. **Client sends DATA message**: Includes Payload and CRC.
2. **Server processes DATA message**:
   - If CRC is valid, server responds with ACK.
   - If CRC is invalid, server responds with ERROR.
3. **Client handles server response**:
   - On receiving ACK, considers data successfully sent.
   - On receiving ERROR or no response within a timeout, may retry sending DATA.

### Error Handling
- A simple error handling is implemented in the python client, by trying to retransmit DATA if ERROR is received

### Communication Flow
- **Client**
  - (Connects)
    - **Server**
     - Send `SERVICE_ANNOUNC_T`
      - **Client**
        - Sends `DATA_T` (data to process)
          - **Server**
            - Receives and processes data
            - Sends `ACK_T` (acknowledgment) or `ERROR_T` (error)
              - **Client**
                - On `ACK_T`
                    - **Server**
                      - Responds with `DATA_T` containing the processed data or `ERROR_T`
                - On `ERROR_T`
                  - Handles the error or retries sending data
