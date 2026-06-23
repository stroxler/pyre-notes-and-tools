"""Advanced creation and ops: tile, repeat, meshgrid, pad, einsum."""

import numpy as np


def tile_and_repeat() -> None:
    a = np.array([1, 2, 3])  # shape: (3,)
    b = np.tile(a, 3)  # shape: (9,)  [1,2,3,1,2,3,1,2,3]
    c = np.tile(a, (2, 3))  # shape: (2, 9)

    d = np.repeat(a, 2)  # shape: (6,)  [1,1,2,2,3,3]

    m = np.array([[1, 2], [3, 4]])  # shape: (2, 2)
    e = np.tile(m, (2, 2))  # shape: (4, 4)
    f = np.repeat(m, 2, axis=0)  # shape: (4, 2)
    g = np.repeat(m, 2, axis=1)  # shape: (2, 4)


def meshgrid_ops() -> None:
    x = np.linspace(0.0, 1.0, 4)  # shape: (4,)
    y = np.linspace(0.0, 1.0, 3)  # shape: (3,)
    xx, yy = np.meshgrid(x, y)  # both shape: (3, 4)

    # Compute distance from origin on the grid
    dist = np.sqrt(xx ** 2 + yy ** 2)  # shape: (3, 4)


def pad_ops() -> None:
    a = np.ones((3, 3))  # shape: (3, 3)
    b = np.pad(a, pad_width=1, mode="constant", constant_values=0)  # shape: (5, 5)
    c = np.pad(a, pad_width=((1, 2), (3, 0)), mode="constant")  # shape: (6, 6)


def einsum_ops() -> None:
    a = np.random.randn(3, 4)
    b = np.random.randn(4, 5)

    # Matrix multiply
    c = np.einsum("ij,jk->ik", a, b)  # shape: (3, 5)

    # Trace
    m = np.random.randn(4, 4)
    t = np.einsum("ii->", m)  # scalar

    # Batch dot product
    x = np.random.randn(10, 3)
    y = np.random.randn(10, 3)
    dots = np.einsum("ij,ij->i", x, y)  # shape: (10,)

    # Outer product
    u = np.random.randn(3)
    v = np.random.randn(4)
    outer = np.einsum("i,j->ij", u, v)  # shape: (3, 4)
