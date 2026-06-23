"""Reductions: sum, mean, min, max, std, var, prod, any, all, with axis."""

import numpy as np


def global_reductions() -> None:
    a = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])  # shape: (2, 3)
    s = np.sum(a)  # scalar: 21.0
    m = np.mean(a)  # scalar: 3.5
    lo = np.min(a)  # scalar: 1.0
    hi = np.max(a)  # scalar: 6.0
    sd = np.std(a)  # scalar
    v = np.var(a)  # scalar
    p = np.prod(a)  # scalar: 720.0


def axis_reductions() -> None:
    a = np.random.randn(3, 4)  # shape: (3, 4)

    # Reduce along axis 0 (collapse rows)
    col_sum = np.sum(a, axis=0)  # shape: (4,)
    col_mean = np.mean(a, axis=0)  # shape: (4,)
    col_min = np.min(a, axis=0)  # shape: (4,)

    # Reduce along axis 1 (collapse cols)
    row_sum = np.sum(a, axis=1)  # shape: (3,)
    row_max = np.max(a, axis=1)  # shape: (3,)


def keepdims_and_bool_reductions() -> None:
    a = np.random.randn(3, 4)  # shape: (3, 4)

    # keepdims preserves reduced axis as size 1
    s = np.sum(a, axis=1, keepdims=True)  # shape: (3, 1)
    normalized = a / s  # broadcasting: (3, 4) / (3, 1) -> (3, 4)

    # Boolean reductions
    b = np.array([True, False, True, True])
    c = np.any(b)  # True
    d = np.all(b)  # False

    m = np.array([[1, 0, 3], [4, 5, 0]])
    e = np.any(m > 0, axis=1)  # shape: (2,)  [True, True]
    f = np.all(m > 0, axis=1)  # shape: (2,)  [False, False]
