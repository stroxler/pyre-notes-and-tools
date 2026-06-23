"""Linear algebra: dot, matmul/@, inner, outer, diag, trace, linalg ops."""

import numpy as np


def products() -> None:
    # Vector dot product
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([4.0, 5.0, 6.0])
    d = np.dot(a, b)  # scalar: 32.0
    d2 = np.inner(a, b)  # scalar: 32.0 (same for 1D)

    # Outer product
    o = np.outer(a, b)  # shape: (3, 3)

    # Matrix multiply
    m1 = np.random.randn(3, 4)
    m2 = np.random.randn(4, 5)
    c = np.matmul(m1, m2)  # shape: (3, 5)
    c2 = m1 @ m2  # shape: (3, 5)

    # Batch matmul
    batch1 = np.random.randn(2, 3, 4)
    batch2 = np.random.randn(2, 4, 5)
    batch_out = batch1 @ batch2  # shape: (2, 3, 5)


def diag_and_trace() -> None:
    m = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    d = np.diag(m)  # shape: (3,)  diagonal: [1, 5, 9]
    t = np.trace(m)  # scalar: 15

    # Construct diagonal matrix from vector
    v = np.array([1.0, 2.0, 3.0])
    dm = np.diag(v)  # shape: (3, 3)


def linalg_ops() -> None:
    a = np.array([[1.0, 2.0], [3.0, 4.0]])

    det = np.linalg.det(a)  # scalar: -2.0
    inv = np.linalg.inv(a)  # shape: (2, 2)
    n = np.linalg.norm(a)  # scalar: Frobenius norm

    # Solve linear system Ax = b
    b = np.array([5.0, 11.0])
    x = np.linalg.solve(a, b)  # shape: (2,)

    # Eigendecomposition
    sym = np.array([[2.0, 1.0], [1.0, 3.0]])
    eigenvalues, eigenvectors = np.linalg.eigh(sym)  # (2,) and (2, 2)
