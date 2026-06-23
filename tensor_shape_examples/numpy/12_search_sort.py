"""Search and sort: sort, argsort, argmin, argmax, nonzero, unique."""

import numpy as np


def sorting() -> None:
    a = np.array([3, 1, 4, 1, 5, 9, 2, 6])
    b = np.sort(a)  # sorted copy: [1, 1, 2, 3, 4, 5, 6, 9]
    idx = np.argsort(a)  # indices that would sort: shape (8,)

    # Sort 2D along an axis
    m = np.random.randint(0, 100, size=(3, 4))  # shape: (3, 4)
    by_col = np.sort(m, axis=0)  # sort each column
    by_row = np.sort(m, axis=1)  # sort each row


def argmin_argmax() -> None:
    a = np.array([10, 5, 30, 15, 25])
    imin = np.argmin(a)  # scalar: 1
    imax = np.argmax(a)  # scalar: 2

    m = np.random.randn(3, 4)  # shape: (3, 4)
    row_maxidx = np.argmax(m, axis=1)  # shape: (3,)
    col_minidx = np.argmin(m, axis=0)  # shape: (4,)


def nonzero_and_unique() -> None:
    a = np.array([0, 3, 0, 5, 7, 0])
    idx = np.nonzero(a)  # tuple of 1 array, shape (3,): [1, 3, 4]

    b = np.array([3, 1, 2, 1, 3, 2, 4])
    u = np.unique(b)  # [1, 2, 3, 4]
    u_sorted, counts = np.unique(b, return_counts=True)  # values and their counts
