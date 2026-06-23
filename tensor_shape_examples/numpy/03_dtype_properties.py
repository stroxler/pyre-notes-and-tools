"""Array properties and dtype conversions: shape, ndim, size, dtype, astype."""

import numpy as np


def inspect_properties() -> None:
    a = np.zeros((3, 4, 5))
    # Scalar properties
    ndim: int = a.ndim  # 3
    size: int = a.size  # 60
    shape: tuple[int, int, int] = a.shape  # (3, 4, 5)
    itemsize: int = a.itemsize  # 8 (float64)
    nbytes: int = a.nbytes  # 480


def dtype_conversions() -> None:
    # Casting between dtypes
    a = np.array([1, 2, 3])  # dtype: int64
    b = a.astype(np.float32)  # dtype: float32, shape unchanged
    c = a.astype(np.float64)  # dtype: float64

    d = np.array([1.7, 2.3, 3.9])
    e = d.astype(np.int32)  # truncates to [1, 2, 3]

    # Creating with explicit dtype
    f = np.zeros((2, 3), dtype=np.int32)
    g = np.ones(5, dtype=np.bool_)
    h = np.arange(10, dtype=np.float32)
