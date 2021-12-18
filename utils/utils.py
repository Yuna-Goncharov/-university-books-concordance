"""
This file contains general utility functions used in multiple places.
"""

import codecs
import functools
import math
import time

# The encoding list to iterate over when trying to open a file
ENCODINGS = "utf-8", None

# The name of the different file sizes
FILE_SIZES = ("Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")


@functools.lru_cache()
def cached_read(filename):
    """
    Read a file and cache the result.
    It handles few kinds of different encodings.
    :param filename: The filename to read
    :raises UnicodeDecodeError: If failed to open the file with all tried encodings
    :return: The content of the file in the assumed encoding
    """
    for encoding in ENCODINGS:
        try:
            with codecs.open(filename, "r", encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            # Continue to next encoding
            pass

    # No encoding was found
    raise UnicodeDecodeError


def float_to_str(number, ndigits=2):
    """
    Round a float and convert it to a string with commas.
    If the float is an integer, no decimal point is needed.
    :param number: The float to convert
    :param ndigits: The wanted precision in decimal digits
    :return: The float as string
    """
    # If result is None, make it a zero
    if number is None:
        number = 0
    elif isinstance(number, float):
        # If result is float, round it to 3 digits
        number = round(number, ndigits)

        # If the result is a float which is a whole number, convert it to int
        if int(number) == number:
            number = int(number)

    # The number as a string with commas
    return f'{number:,}'


def file_size_to_str(file_size, ndigits=2):
    """
    Convert a file size integer to a string with the correct unit.
    :param file_size: The file size in bytes
    :param ndigits: The wanted precision in decimal digits
    :return: The file size as string
    """
    if not file_size:
        return f"0 {FILE_SIZES[0]}"

    # Calculate the the biggest power of 1024 that is smallest then file_size
    biggest_power = int(math.floor(math.log(file_size, 1024)))
    assert biggest_power < len(FILE_SIZES)

    # Calculate the file size in the selected units
    unit_size = math.pow(1024, biggest_power)
    size_in_units = file_size / unit_size

    return f"{float_to_str(size_in_units, ndigits)} {FILE_SIZES[biggest_power]}"


def timeit(func):
    """
    Decorator for printing the execution time of a function.
    Used for debugging purposes, for performance improvements.
    :param func: The method to decorate
    :return: Decorated function
    """
    def timed(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print('%r %2.2f ms' % (func.__name__, (end_time - start_time) * 1000))
        return result

    return timed
