"""Reshaping: reshape, flatten, ravel, transpose, squeeze, expand_dims."""

import numpy as np


def reshape_basics() -> None:
    a = np.arange(12)  # shape: (12,)
    b = a.reshape(3, 4)  # shape: (3, 4)
    c = a.reshape(2, 6)  # shape: (2, 6)
    d = a.reshape(2, 2, 3)  # shape: (2, 2, 3)
    e = a.reshape(4, -1)  # shape: (4, 3)  -1 inferred


def flatten_and_ravel() -> None:
    a = np.array([[1, 2, 3], [4, 5, 6]])  # shape: (2, 3)
    b = a.flatten()  # shape: (6,)  always a copy
    c = a.ravel()  # shape: (6,)  view when possible
    d = np.reshape(a, -1)  # shape: (6,)  function form


def transpose_ops() -> None:
    a = np.ones((3, 4))  # shape: (3, 4)
    b = a.T  # shape: (4, 3)
    c = a.transpose()  # shape: (4, 3)
    d = np.transpose(a)  # shape: (4, 3)

    # Higher-dimensional transpose
    e = np.zeros((2, 3, 4))  # shape: (2, 3, 4)
    f = e.transpose(1, 0, 2)  # shape: (3, 2, 4)
    g = e.transpose(2, 0, 1)  # shape: (4, 2, 3)


def squeeze_and_expand() -> None:
    a = np.zeros((1, 3, 1, 4))  # shape: (1, 3, 1, 4)
    b = a.squeeze()  # shape: (3, 4)
    c = np.squeeze(a, axis=0)  # shape: (3, 1, 4)

    d = np.zeros((3, 4))  # shape: (3, 4)
    e = np.expand_dims(d, axis=0)  # shape: (1, 3, 4)
    f = np.expand_dims(d, axis=-1)  # shape: (3, 4, 1)
    g = d[:, np.newaxis, :]  # shape: (3, 1, 4)
