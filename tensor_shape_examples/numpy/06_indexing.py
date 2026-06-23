"""Indexing: basic, slicing, boolean, fancy, combined."""

import numpy as np


def basic_and_slicing() -> None:
    a = np.arange(10)  # shape: (10,)
    s = a[3]  # scalar
    b = a[2:7]  # shape: (5,)
    c = a[::2]  # shape: (5,)  every other element
    d = a[::-1]  # shape: (10,)  reversed

    m = np.arange(12).reshape(3, 4)  # shape: (3, 4)
    row = m[1]  # shape: (4,)  second row
    elem = m[1, 2]  # scalar
    sub = m[0:2, 1:3]  # shape: (2, 2)


def boolean_indexing() -> None:
    a = np.array([10, 20, 30, 40, 50])
    mask = a > 25  # shape: (5,)  dtype: bool
    b = a[mask]  # shape: dynamic, values [30, 40, 50]

    m = np.random.randn(4, 4)
    pos = m[m > 0]  # 1D, positive elements only

    # Setting values via boolean mask
    c = a.copy()
    c[c < 30] = 0  # [0, 0, 30, 40, 50]


def fancy_indexing() -> None:
    a = np.array([10, 20, 30, 40, 50])
    idx = np.array([0, 3, 4])
    b = a[idx]  # shape: (3,)  values [10, 40, 50]

    m = np.arange(12).reshape(3, 4)
    rows = np.array([0, 2])
    cols = np.array([1, 3])
    c = m[rows, cols]  # shape: (2,)  elements m[0,1] and m[2,3]
    d = m[rows]  # shape: (2, 4)  rows 0 and 2
