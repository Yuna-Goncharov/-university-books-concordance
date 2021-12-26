
import codecs
import functools
import math
import time

ENCODINGS = "utf-8", None


FILE_SIZES = ("Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")


@functools.lru_cache()
def cached_read(filename):

    for encoding in ENCODINGS:
        try:
            with codecs.open(filename, "r", encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            pass

    raise UnicodeDecodeError


def float_to_str(number, ndigits=2):

    if number is None:
        number = 0
    elif isinstance(number, float):
        number = round(number, ndigits)

        if int(number) == number:
            number = int(number)

    return f'{number:,}'


def file_size_to_str(file_size, ndigits=2):
    if not file_size:
        return f"0 {FILE_SIZES[0]}"

    biggest_power = int(math.floor(math.log(file_size, 1024)))
    assert biggest_power < len(FILE_SIZES)

    unit_size = math.pow(1024, biggest_power)
    size_in_units = file_size / unit_size

    return f"{float_to_str(size_in_units, ndigits)} {FILE_SIZES[biggest_power]}"


def timeit(func):
    def timed(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print('%r %2.2f ms' % (func.__name__, (end_time - start_time) * 1000))
        return result

    return timed
