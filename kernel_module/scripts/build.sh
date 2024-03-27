#!/bin/bash

# This module is used for unloading, removing, building and loading a Linux kernel module.
# It is useful for developing kernel module allowing quick changes.

# Adjust those variables to your specific kernel module setup
MODULE_NAME="math_chardev"
BUILD_DIR="../build/"   # Kernel module build output dir

main() {
    # Ensure calling the script from the right directory
    KERNEL_MOD_DIR=$(dirname $(dirname $(realpath $0)))  # Directory of the kernel source
    cd "$KERNEL_MOD_DIR" || { echo "ERROR: Failed to change directory to $KERNEL_MOD_DIR"; exit 1; }

    # Check if the script is run as sudo
    if [ "$EUID" -ne 0 ]; then
        echo "ERROR: The script must be run as sudo!"
        exit 1
    fi

    lsmod | grep $MODULE_NAME > /dev/null
    if [ $? -eq 0 ]; then
        echo "Module $MODULE_NAME is loaded, unloading now..."
        
        # Unload the module
        rmmod $MODULE_NAME || { echo "ERROR: Failed to unload $MODULE_NAME"; exit 1; }

        # Remove the device file
        rm /dev/$MODULE_NAME || { echo "ERROR: Failed to remove device file /dev/$MODULE_NAME"; exit 1; }
    else
        echo "Module $MODULE_NAME is not loaded."
    fi


    # Check if ../build/ contains *chardev* files
    if ls $BUILD_DIR/*chardev* 1> /dev/null 2>&1; then
        echo "Running make clean, found build *chardev* files in $BUILD_DIR..."
        make clean || { echo "ERROR: Failed to clean. Aborting."; exit 1; }
    else
        echo "No *chardev* files in $BUILD_DIR, skipping make clean."
    fi

    # Build the module
    make all || { echo "ERROR: Build failed. Aborting."; exit 1; }

    # Load the chardev module
    scripts/load_chardev.sh $MODULE_NAME $BUILD_DIR || { echo "ERROR: Failed to load $MODULE_NAME. Aborting."; exit 1; }
}

# Entry point
main
