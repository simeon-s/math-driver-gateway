#!/bin/bash

INPUT_DIR="./test/py_client_server/mock_data"

OUTPUT_DIR="./test/py_client_server/output"
INPUT_LISTS=("${INPUT_DIR}/test1_input.txt" "${INPUT_DIR}/test2_input.txt" "${INPUT_DIR}/test3_input.txt")

mkdir -p $OUTPUT_DIR

# Counter for naming output files
COUNTER=1

# Run each test in parallel and redirect output to separate files
for INPUT in "${INPUT_LISTS[@]}"; do
    echo "Running test with input: $INPUT"
    python3 -m ipc.py_client.client "$INPUT" > "${OUTPUT_DIR}/test_output$COUNTER.log" 2>&1 &
    let COUNTER=COUNTER+1
done

# Wait for all background processes to finish
wait

echo "All tests completed. Check test_output*.log files for results."
