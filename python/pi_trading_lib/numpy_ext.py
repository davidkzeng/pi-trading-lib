import numpy as np


def pos(arr: np.ndarray) -> np.ndarray:
    return np.maximum(np.zeros(arr.shape), arr)  # type: ignore


def neg(arr: np.ndarray) -> np.ndarray:
    return np.minimum(np.zeros(arr.shape), arr)  # type: ignore
