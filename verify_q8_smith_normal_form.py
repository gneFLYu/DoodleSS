"""Verify the Smith normal form of the Q8 period-relation matrix.

Run with:

    python verify_q8_smith_normal_form.py

Only NumPy is required.  Arrays use ``dtype=object`` so that all arithmetic
is performed with Python integers rather than floating-point numbers.
"""

from itertools import combinations
from math import gcd

import numpy as np


def integer_matrix(rows: list[list[int]]) -> np.ndarray:
    """Construct a NumPy matrix with exact Python-integer entries."""
    return np.array(rows, dtype=object)


def bareiss_det(matrix: np.ndarray) -> int:
    """Compute an exact determinant using fraction-free elimination."""
    a = matrix.copy()
    n = a.shape[0]
    if n == 0:
        return 1

    sign = 1
    previous_pivot = 1
    for k in range(n - 1):
        if a[k, k] == 0:
            swap_row = next((i for i in range(k + 1, n) if a[i, k] != 0), None)
            if swap_row is None:
                return 0
            a[[k, swap_row]] = a[[swap_row, k]]
            sign *= -1

        pivot = a[k, k]
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                numerator = a[i, j] * pivot - a[i, k] * a[k, j]
                assert numerator % previous_pivot == 0
                a[i, j] = numerator // previous_pivot
        for i in range(k + 1, n):
            a[i, k] = 0
        previous_pivot = pivot

    return sign * int(a[n - 1, n - 1])


def determinantal_divisors(matrix: np.ndarray) -> list[int]:
    """Return gcds of all square minors of each possible positive size."""
    m, n = matrix.shape
    divisors: list[int] = []
    for size in range(1, min(m, n) + 1):
        minor_gcd = 0
        for rows in combinations(range(m), size):
            for cols in combinations(range(n), size):
                minor = matrix[np.ix_(rows, cols)]
                minor_gcd = gcd(minor_gcd, abs(bareiss_det(minor)))
        divisors.append(minor_gcd)
    return divisors


A = integer_matrix(
    [
        [1, 1, 1, 1, 1],
        [4, 4, -4, -4, 0],
        [4, -4, 4, -4, 0],
        [4, -4, -4, 4, 0],
        [10, 10, -2, -2, -4],
        [10, -2, 10, -2, -4],
        [10, -2, -2, 10, -4],
        [16, 16, 0, 0, -8],
        [16, 0, 16, 0, -8],
        [16, 0, 0, 16, -8],
    ]
)

U = integer_matrix(
    [
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [2, -9, 15, -3, 7, -9, 3, 0, 0, 0],
        [0, 11, -15, 5, -7, 10, -3, 0, 0, 0],
        [0, -3, 5, -1, 2, -3, 1, 0, 0, 0],
        [8, -23, 40, -8, 18, -24, 8, 0, 0, 0],
        [0, -3, 3, 0, 2, -2, 0, 0, 0, 0],
        [0, 6, -9, 3, -4, 6, -2, 0, 0, 0],
        [0, 1, 0, 0, -2, 0, 0, 1, 0, 0],
        [0, 57, -80, 24, -38, 52, -16, 0, 1, 0],
        [0, -39, 60, -20, 26, -40, 12, 0, 0, 1],
    ]
)

V = integer_matrix(
    [
        [0, 0, 0, 0, 1],
        [0, 0, 0, -1, 1],
        [0, 0, -1, 0, 1],
        [1, 1, 1, 1, -15],
        [0, -1, 0, 0, 12],
    ]
)

V_inverse = integer_matrix(
    [
        [1, 1, 1, 1, 1],
        [12, 0, 0, 0, -1],
        [1, 0, -1, 0, 0],
        [1, -1, 0, 0, 0],
        [1, 0, 0, 0, 0],
    ]
)

D = np.zeros((10, 5), dtype=object)
for index, value in enumerate([1, 2, 4, 4, 64]):
    D[index, index] = value


def main() -> None:
    computed = U @ A @ V
    delta = determinantal_divisors(A)
    invariant_factors = [delta[0]] + [
        delta[i] // delta[i - 1] for i in range(1, len(delta))
    ]

    print("U A V =")
    print(computed)
    print()
    print("Expected Smith matrix D =")
    print(D)
    print()

    assert np.array_equal(computed, D), "U @ A @ V is not D"
    assert bareiss_det(U) == 1, "U is not unimodular"
    assert bareiss_det(V) == 1, "V is not unimodular"
    assert np.array_equal(V @ V_inverse, np.eye(5, dtype=object))
    assert delta == [1, 2, 8, 32, 2048]
    assert invariant_factors == [1, 2, 4, 4, 64]

    print(f"det(U) = {bareiss_det(U)}")
    print(f"det(V) = {bareiss_det(V)}")
    print(f"determinantal divisors = {delta}")
    print(f"invariant factors      = {invariant_factors}")
    print("V @ V_inverse is the identity matrix")
    print()
    print("All exact-integer checks passed.")


if __name__ == "__main__":
    main()
