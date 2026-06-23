"""Cumulative and statistical: cumsum, cumprod, diff, histogram, bincount."""

import numpy as np


def cumulative_ops() -> None:
    a = np.array([1, 2, 3, 4, 5])
    cs = np.cumsum(a)  # [1, 3, 6, 10, 15]
    cp = np.cumprod(a)  # [1, 2, 6, 24, 120]
    d = np.diff(a)  # [1, 1, 1, 1]  shape: (4,)

    # Along axis
    m = np.array([[1, 2, 3], [4, 5, 6]])  # shape: (2, 3)
    cs_rows = np.cumsum(m, axis=1)  # shape: (2, 3)
    d_cols = np.diff(m, axis=0)  # shape: (1, 3)


def histogram_and_bincount() -> None:
    data = np.random.randn(1000)  # shape: (1000,)

    # Histogram
    counts, bin_edges = np.histogram(data, bins=10)
    # counts: shape (10,), bin_edges: shape (11,)

    counts2, edges2 = np.histogram(data, bins=np.linspace(-3.0, 3.0, 7))
    # counts2: shape (6,), edges2: shape (7,)

    # Bincount for non-negative integer arrays
    labels = np.array([0, 1, 1, 2, 2, 2, 3])
    bc = np.bincount(labels)  # [1, 2, 3, 1]

    # Weighted bincount
    weights = np.array([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5])
    wbc = np.bincount(labels, weights=weights)  # weighted sums per bin
