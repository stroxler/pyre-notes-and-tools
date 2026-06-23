"""Element-wise arithmetic: operators, np.abs, np.negative, scalar ops."""

import numpy as np


def basic_ops() -> None:
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([10.0, 20.0, 30.0, 40.0])

    # Binary operators: shape preserved
    c = a + b  # [11, 22, 33, 44]
    d = a - b  # [-9, -18, -27, -36]
    e = a * b  # [10, 40, 90, 160]
    f = b / a  # [10, 10, 10, 10]
    g = b // a  # [10, 10, 10, 10]
    h = b % a  # [0, 0, 0, 0]

    # Scalar arithmetic: broadcasts scalar to array shape
    x = a * 2.0  # [2, 4, 6, 8]
    y = a + 1.0  # [2, 3, 4, 5]
    z = a ** 2  # [1, 4, 9, 16]


def unary_ops() -> None:
    a = np.array([-3.0, -1.0, 0.0, 2.0, 5.0])

    b = np.abs(a)  # [3, 1, 0, 2, 5]
    c = np.negative(a)  # [3, 1, 0, -2, -5]
    d = -a  # same as negative
    e = +a  # unary positive (copy)


def matrix_arithmetic() -> None:
    # 2D element-wise ops
    a = np.ones((3, 4))
    b = np.full((3, 4), 2.0)

    c = a + b  # shape: (3, 4), all 3.0
    d = a * b  # shape: (3, 4), all 2.0
    e = b ** 2  # shape: (3, 4), all 4.0
