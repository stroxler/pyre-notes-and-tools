"""Math ufuncs: sqrt, exp, log, trig, floor, ceil, clip, minimum, maximum."""

import numpy as np


def exponential_and_log() -> None:
    a = np.array([0.0, 1.0, 2.0, 3.0])
    b = np.exp(a)  # [1, e, e^2, e^3]
    c = np.log(b)  # [0, 1, 2, 3]  roundtrip
    d = np.log2(np.array([1.0, 2.0, 4.0, 8.0]))  # [0, 1, 2, 3]
    e = np.log10(np.array([1.0, 10.0, 100.0]))  # [0, 1, 2]

    f = np.sqrt(np.array([0.0, 1.0, 4.0, 9.0]))  # [0, 1, 2, 3]
    g = np.power(a, 2)  # [0, 1, 4, 9]


def trigonometry() -> None:
    angles = np.linspace(0.0, 2 * np.pi, 8)  # shape: (8,)
    s = np.sin(angles)  # shape: (8,)
    c = np.cos(angles)  # shape: (8,)
    t = np.tan(angles[:4])  # shape: (4,)

    # Inverse trig
    a = np.arcsin(np.array([0.0, 0.5, 1.0]))  # shape: (3,)
    b = np.arctan2(np.array([1.0, 0.0]), np.array([0.0, 1.0]))  # shape: (2,)


def rounding_and_clipping() -> None:
    a = np.array([-1.7, -0.3, 0.5, 1.2, 2.9])
    b = np.floor(a)  # [-2, -1, 0, 1, 2]
    c = np.ceil(a)  # [-1, 0, 1, 2, 3]
    d = np.round(a)  # [-2, 0, 0, 1, 3]
    e = np.trunc(a)  # [-1, 0, 0, 1, 2]

    f = np.clip(a, -1.0, 2.0)  # [-1, -0.3, 0.5, 1.2, 2]
    g = np.minimum(a, np.zeros_like(a))  # clamp to <= 0
    h = np.maximum(a, np.zeros_like(a))  # clamp to >= 0
