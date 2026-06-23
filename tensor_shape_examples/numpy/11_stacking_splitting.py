"""Stacking and splitting: concatenate, stack, vstack, hstack, split."""

import numpy as np


def concatenate_ops() -> None:
    a = np.ones((2, 3))  # shape: (2, 3)
    b = np.zeros((2, 3))  # shape: (2, 3)

    # Concatenate along axis 0 (stack vertically)
    c = np.concatenate([a, b], axis=0)  # shape: (4, 3)

    # Concatenate along axis 1 (stack horizontally)
    d = np.concatenate([a, b], axis=1)  # shape: (2, 6)

    # 1D concatenation
    e = np.concatenate([np.arange(3), np.arange(4)])  # shape: (7,)


def stack_ops() -> None:
    a = np.ones(4)  # shape: (4,)
    b = np.zeros(4)  # shape: (4,)

    # stack adds a new axis
    c = np.stack([a, b])  # shape: (2, 4)
    d = np.stack([a, b], axis=1)  # shape: (4, 2)

    # Convenience shortcuts
    e = np.vstack([a, b])  # shape: (2, 4)  vertical
    f = np.hstack([a, b])  # shape: (8,)  horizontal for 1D

    # 2D convenience
    m1 = np.ones((2, 3))
    m2 = np.zeros((2, 3))
    g = np.vstack([m1, m2])  # shape: (4, 3)
    h = np.hstack([m1, m2])  # shape: (2, 6)


def split_ops() -> None:
    a = np.arange(12).reshape(3, 4)  # shape: (3, 4)

    # Split into equal parts along axis 1
    parts = np.split(a, 2, axis=1)  # list of 2 arrays, each (3, 2)
    p0 = parts[0]  # shape: (3, 2)
    p1 = parts[1]  # shape: (3, 2)

    # Split 1D
    b = np.arange(9)
    chunks = np.split(b, 3)  # list of 3 arrays, each (3,)
