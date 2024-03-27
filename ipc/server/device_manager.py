import logging
import os

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-5s | %(threadName)s | %(message)s",
)


class DeviceManager:
    READ_BUFFER_SIZE = 256

    def __init__(self, device_path):
        self.device_path = device_path
        self.device_file = None

    def open_device(self):
        try:
            if self.device_file is None:
                self.device_file = open(self.device_path, "rb+", buffering=0)
                logging.info("Device opened!")
        except Exception as e:
            logging.error(f"Error opening device file: {e}")
            self.device_file = None

    def close_device(self):
        try:
            if self.device_file:
                self.device_file.close()
                logging.info("Device closed!")
        except Exception as e:
            logging.error(f"Error closing device file: {e}")
        finally:
            self.device_file = None

    def write_to_device(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        try:
            if self.device_file:
                self.device_file.write(data)
                self.device_file.flush()
                return 0
            else:
                logging.error("Attempt to write when device file is not open.")
        except OSError as e:
            if e.errno == 34:  # Numerical result out of range
                logging.error(f"Error writing to device: {e}")
            else:
                logging.error(f"OS error occurred: {e}")
            return e.errno
        except Exception as e:
            logging.error(f"Unexpected error writing to device: {e}")
            return 1

    def read_from_device(self):
        if self.device_file is None:
            logging.error("Cannot read the device!")
            return None

        try:
            if not self.device_file.seekable():
                logging.error("Device file does not support seeking!")
                return None

            self.device_file.seek(0)
            data = self.device_file.read(self.READ_BUFFER_SIZE)

            if data is None:
                logging.error("No data read from the device!")
                return None

            return data.decode("utf-8").strip()

        except Exception as e:
            logging.error(f"Error reading from device: {e}")
            return None
