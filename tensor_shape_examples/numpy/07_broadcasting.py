"""Broadcasting: scalar+array, row+col, matrix+vector patterns."""

import numpy as np


def scalar_broadcasting() -> None:
    a = np.ones((3, 4))  # shape: (3, 4)
    b = a + 5.0  # shape: (3, 4)  scalar broadcasts
    c = a * 2.0  # shape: (3, 4)
    d = 1.0 / (a + 1.0)  # shape: (3, 4)


def vector_matrix_broadcasting() -> None:
    m = np.ones((3, 4))  # shape: (3, 4)
    row = np.array([1.0, 2.0, 3.0, 4.0])  # shape: (4,)
    col = np.array([[10.0], [20.0], [30.0]])  # shape: (3, 1)

    # row broadcasts across rows: (3,4) + (4,) -> (3,4)
    a = m + row

    # col broadcasts across cols: (3,4) + (3,1) -> (3,4)
    b = m + col

    # row * col outer-product-style: (3,1) * (4,) -> (3,4)
    c = col * row


def higher_dim_broadcasting() -> None:
    # 3D broadcasting patterns
    a = np.random.randn(2, 3, 4)  # shape: (2, 3, 4)
    b = np.random.randn(4)  # shape: (4,)
    c = a + b  # shape: (2, 3, 4)

    d = np.random.randn(3, 1)  # shape: (3, 1)
    e = a + d  # shape: (2, 3, 4)

    f = np.random.randn(2, 1, 1)  # shape: (2, 1, 1)
    g = a * f  # shape: (2, 3, 4)
