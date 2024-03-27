OUTPUT_DIR = ../../build/c_client

all: $(OUTPUT_DIR)/main

$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)

$(OUTPUT_DIR)/main: main.c protocol.c | $(OUTPUT_DIR)
	gcc -o $(OUTPUT_DIR)/main main.c protocol.c -lz

clean:
	rm -f $(OUTPUT_DIR)/main
