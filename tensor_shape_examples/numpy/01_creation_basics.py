"""Array creation basics: array, zeros, ones, full, arange, linspace, eye, empty."""

import numpy as np


def scalar_and_1d() -> None:
    # Scalar and 1D creation
    s = np.array(0.5)  # shape: ()
    a = np.array([1, 2, 3])  # shape: (3,)
    b = np.zeros(5)  # shape: (5,)
    c = np.ones(4)  # shape: (4,)
    d = np.full(3, 7.0)  # shape: (3,)
    e = np.empty(6)  # shape: (6,)


def ranges_and_linspace() -> None:
    # arange and linspace for 1D sequences
    a = np.arange(10)  # shape: (10,)  dtype: int
    b = np.arange(2.0, 8.0, 0.5)  # shape: (12,)  dtype: float
    c = np.linspace(0.0, 1.0, 5)  # shape: (5,)
    d = np.linspace(0.0, 2 * np.pi, 100)  # shape: (100,)


def matrix_creation() -> None:
    # 2D creation with shape tuples
    a = np.zeros((3, 4))  # shape: (3, 4)
    b = np.ones((2, 5))  # shape: (2, 5)
    c = np.full((3, 3), -1.0)  # shape: (3, 3)
    d = np.eye(4)  # shape: (4, 4)
    e = np.array([[1, 2], [3, 4], [5, 6]])  # shape: (3, 2)
