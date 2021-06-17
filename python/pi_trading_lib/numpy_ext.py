import numpy as np
import pandas as pd


def pos(arr: np.ndarray) -> np.ndarray:
    return np.maximum(np.zeros(arr.shape), arr)  # type: ignore


def neg(arr: np.ndarray) -> np.ndarray:
    return np.minimum(np.zeros(arr.shape), arr)  # type: ignore


def reindex(arr: np.ndarray, src_index: np.ndarray, target_index: np.ndarray) -> np.ndarray:
    assert arr.ndim == 1
    assert target_index.ndim == 1
    assert arr.shape == src_index.shape

    ser = pd.Series(arr, index=src_index)
    ser = ser.reindex(target_index)
    return ser.to_numpy()  # type: ignore
