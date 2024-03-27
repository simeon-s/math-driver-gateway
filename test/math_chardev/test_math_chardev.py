"""
This module tests the math kernel device for operations with 32-bit signed integers.
It tests addition, subtraction, multiplication and division.
"""
import errno
import pytest

DEVICE_PATH = "/dev/math_chardev"

test_cases = {
    "3 + 4": ("7", None),
    "10 - 4": ("6", None),
    "5 * 3": ("15", None),
    "12 / 3": ("4", None),
    "5 / 2": ("2", None),                               # Integer division resulting a fraction
    "2147483647 + 1": (None, errno.ERANGE),             # Max 32-bit int overflow for addition
    "-2147483648 - 1": (None, errno.ERANGE),            # Min 32-bit int underflow for subtraction
    "2147483647 * 2": (None, errno.EOVERFLOW),          # Overflow for multiplication
    "-2147483648 * 2": (None, errno.EOVERFLOW),         # Underflow for multiplication
    "-2147483648 - 1": (None, errno.ERANGE),            # Underflow for subtraction
    "10 / 0": (None, errno.EOVERFLOW),                  # Division by zero
    "9999999999 + 1": (None, errno.ERANGE),             # Number outside 32-bit int range
    "a + b": (None, errno.EDOM),                        # Non-integer input
    "1 + 2 + 3": (None, errno.EDOM),                    # Multiple operands input
    "-2147483648 / -1": (None, errno.EINVAL),           # Specific edge case for signed int division
    "3.5 + 4.2": (None, errno.EDOM),                    # Float addition
    "10.0 - 4.8": (None, errno.EDOM),                   # Float subtraction
    "5.2 * 3.1": (None, errno.EDOM),                    # Float multiplication
    "12.0 / 3.0": (None, errno.EDOM),                   # Float division
    "2147483647 * 2147483647": (None, errno.EOVERFLOW), # Overflow for multiplication
    "-2147483648 / -1": (None, errno.EOVERFLOW),        # Overflow for division
    "2147483647 / 0.5": (None, errno.EDOM),             # Overflow for division
}

def write_to_device(data):
    with open(DEVICE_PATH, "w", encoding='utf-8') as device_file:
        device_file.write(data)

def read_from_device():
    with open(DEVICE_PATH, "r", encoding='utf-8') as device_file:
        return device_file.read().strip()

@pytest.mark.parametrize("expression, expected_result", test_cases.items())
def test_math_chardev(expression, expected_result):
    expected_output, expected_errno = expected_result
    if expected_errno is not None:
        with pytest.raises(OSError) as exc_info:
            write_to_device(expression)
        assert exc_info.value.errno == expected_errno, \
               f"Expected errno {expected_errno}, got {exc_info.value.errno}"
    else:
        write_to_device(expression)
        result = read_from_device()
        assert result == expected_output
