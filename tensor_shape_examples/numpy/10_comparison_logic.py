"""Comparisons and logic: relational ops, logical ops, where, isnan, allclose."""

import numpy as np


def comparisons() -> None:
    a = np.array([1, 2, 3, 4, 5])
    b = np.array([5, 4, 3, 2, 1])

    # Element-wise comparisons produce bool arrays, shape preserved
    eq = a == b  # [F, F, T, F, F]
    lt = a < b  # [T, T, F, F, F]
    ge = a >= b  # [F, F, T, T, T]
    ne = a != b  # [T, T, F, T, T]


def logical_ops() -> None:
    a = np.array([True, True, False, False])
    b = np.array([True, False, True, False])

    c = np.logical_and(a, b)  # [T, F, F, F]
    d = np.logical_or(a, b)  # [T, T, T, F]
    e = np.logical_not(a)  # [F, F, T, T]
    f = np.logical_xor(a, b)  # [F, T, T, F]

    # Operator equivalents on bool arrays
    g = a & b  # same as logical_and
    h = a | b  # same as logical_or
    i = ~a  # same as logical_not


def where_and_special_checks() -> None:
    a = np.array([1.0, -2.0, 3.0, -4.0, 5.0])

    # np.where: condition ? x : y, element-wise
    b = np.where(a > 0, a, 0.0)  # [1, 0, 3, 0, 5]

    c = np.array([1.0, np.nan, 3.0, np.inf, -np.inf])
    d = np.isnan(c)  # [F, T, F, F, F]
    e = np.isinf(c)  # [F, F, F, T, T]
    f = np.isfinite(c)  # [T, F, T, F, F]

    g = np.allclose(np.array([1.0, 2.0]), np.array([1.0, 2.0 + 1e-10]))  # True
    h = np.array_equal(np.array([1, 2]), np.array([1, 2]))  # True
