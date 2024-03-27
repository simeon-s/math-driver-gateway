#!/bin/bash

# This script is used to load kernel module and create a device file, setting its permission.

# Check for required input arguments
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "ERROR: Missing arguments."
  echo "Usage: $0 module_name build_directory"
  exit 1
fi

MODULE_NAME="$1"
BUILD_DIR="$2"

# Check if the script is run as sudo
if [ "$EUID" -ne 0 ]; then
  echo "ERROR: The script must be run as sudo!"
  exit 1
fi

# Change directory to $BUILD_DIR
cd "$BUILD_DIR" || { echo "ERROR: Failed to change directory to $BUILD_DIR"; exit 1; }

# Load the module
insmod "${MODULE_NAME}.ko" || { echo "ERROR: Failed to load ${MODULE_NAME} module"; exit 1; }

# Get the major number
MAJOR=$(awk "\$2==\"$MODULE_NAME\" {print \$1}" /proc/devices) || { echo "ERROR: Failed to retrieve major number"; exit 1; }

# Check if MAJOR is empty
if [ -z "$MAJOR" ]; then
  echo "ERROR: No major number found for $MODULE_NAME"
  exit 1
fi

# Create the device file
mknod "/dev/$MODULE_NAME" c "$MAJOR" 0 || { echo "ERROR: Failed to create device file"; exit 1; }

# Change permissions of the device file
chmod 666 "/dev/$MODULE_NAME" || { echo "ERROR: Failed to change permissions for /dev/$MODULE_NAME"; exit 1; }

echo "Test the module..."
echo "1+2" | tee "/dev/$MODULE_NAME" || { echo "ERROR: Failed to write to /dev/$MODULE_NAME"; exit 1; }
echo "Result: "
cat "/dev/$MODULE_NAME" || { echo "ERROR: Failed to read from /dev/$MODULE_NAME"; exit 1; }
