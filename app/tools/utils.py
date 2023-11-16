import time
from functools import wraps
from typing import NotRequired, TypeAlias, TypedDict

import numpy as np


def minmax(x):
    return [np.min(x), np.max(x)]


def pad(x, n):
    return np.pad(x, (0, n - len(x)), mode="constant")


def fft(x):
    return np.fft.fft(x)


class PeakDatum(TypedDict):
    position: float
    fwhm: NotRequired[float]


class PeakData(TypedDict):
    peaks: list[PeakDatum]


class ProcessingMessage(TypedDict):
    message: str
    execution_time: NotRequired[float]


def np_encoder(object):
    if isinstance(object, np.generic):
        return object.item()


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        result["execution_time"] = total_time
        return result

    return timeit_wrapper


DEGREE = 0.0174533
FIT_FREQ_INTERVAL = (0.1, 0.5)
COMMON_RANGE_FREQ_INTERVAL = (0.2, 1.0)
SPEED_C = 360
URL: TypeAlias = str
