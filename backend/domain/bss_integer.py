"""Exact additive integer Q8 2-BSS pages in DKLLW-normalized notation.

The primary E1 algebra is Beaudry17b Appendix A (by H.-W. Henn),
Theorems A.14/A.20, with x_Bea = D*x and y_Bea = D**2*y. Integer
Bockstein equations are from Bauer08 Section 7, printed pp. 28-29;
DKLLW24 Table 1 is the secondary normalized presentation. Bauer prints
the final equation as d4(y h2^2)=8g, whereas the h0-adic convention used
here (and DKLLW) numbers it d3. This discrepancy is not silently treated
as agreement of the printed page labels. The displayed grading
is (internal degree - cohomological degree, cohomological degree).  A
d_r has degree (-1,+1) there and raises the independent h0 grading by r.

This is the associated-graded 2-BSS, not its hidden-extension algebra,
not a completed coefficient ring, and not the subsequent HFPSS.  Arbitrary
D, k and h0 exponents have exact symbolic support.  A finite viewport is
only an enumeration request and never participates in deciding page fate.

All nonzero differential columns in this basis have coefficient 1 in F4,
so their kernels/images are coordinate subspaces.  F4 scalar multiples of
a basis vector inherit the maps below by linearity.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterator


BASIS_GRADES: dict[str, tuple[int, int]] = {
    "1": (0, 0), "h1": (1, 1), "h1^2": (2, 2), "h1^3": (3, 3),
    "x": (-1, 1), "xh1": (0, 2), "x^2": (-2, 2), "x^2h1": (-1, 3),
    "h2": (3, 1), "y": (-1, 1), "h2^2": (6, 2), "yh2": (2, 2),
    "h2^3": (9, 3), "x^3": (-3, 3),
}
FREE_BASES = ("1", "h1", "h1^2", "h1^3")
V1_LENGTH_TWO_BASES = ("x", "xh1", "x^2", "x^2h1")
V1_LENGTH_ONE_BASES = ("h2", "y", "h2^2", "yh2", "h2^3", "x^3")
SOURCE_REFS = (
    "Beaudry17b, Appendix A by H.-W. Henn, Theorems A.14 and A.20 (PDF pp. 57, 61-62): primary E1 algebra and multiplication",
    "Bauer08, Section 7, printed pp. 28-29 (PDF pp. 18-19): primary integer Bockstein equations; final 8g row printed d4, represented as d3 in the present h0-adic convention",
    "DKLLW24, Lemma 3.1, Proposition 3.2 and Table 1 (journal PDF pp. 19-21): Q8 notation comparison and secondary page convention",
)


def _integer(value: int, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class BSSMonomial:
    """A nonzero canonical E1 basis vector.

    The represented vector is basis * v1**v1 * k**k * D**D * h0**h0.
    These are independent F4 basis vectors, not a presentation in which
    out-of-range powers may silently denote zero.  Invalid tuples raise.
    """

    basis: str
    v1: int = 0
    k: int = 0
    D: int = 0
    h0: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.basis, str) or self.basis not in BASIS_GRADES:
            raise ValueError("Unknown canonical 2-BSS additive basis label")
        for name in ("v1", "k", "h0"):
            _integer(getattr(self, name), name, minimum=0)
        _integer(self.D, "D")
        if self.basis in V1_LENGTH_TWO_BASES and self.v1 > 1:
            raise ValueError(f"{self.basis} is annihilated by v1^2")
        if self.basis in V1_LENGTH_ONE_BASES and self.v1:
            raise ValueError(f"{self.basis} is annihilated by v1")

    def as_tuple(self) -> tuple[str, int, int, int, int]:
        return self.basis, self.v1, self.k, self.D, self.h0

    @property
    def bidegree(self) -> tuple[int, int]:
        stem, filtration = BASIS_GRADES[self.basis]
        return stem + 2*self.v1 - 4*self.k + 8*self.D, filtration + 4*self.k

    @property
    def tridegree(self) -> tuple[int, int, int]:
        return *self.bidegree, self.h0


def _page(page: int) -> int:
    return _integer(page, "page", minimum=1)


def is_live(monomial: BSSMonomial, page: int) -> bool:
    """Whether this canonical vector is a nonzero basis class on E_page.

    E1 begins before d1. E4 is E-infinity for this auxiliary sequence;
    page numbers greater than four have the same answer. No view bounds,
    enumeration limits, or other spectral sequences enter this predicate.
    """
    _page(page)
    if not isinstance(monomial, BSSMonomial):
        raise TypeError("monomial must be a BSSMonomial")
    if page == 1:
        return True
    basis, v1, k, _, h0 = monomial.as_tuple()

    # E2: remove every nonzero d1 source and every positive-h0 target layer.
    if basis in FREE_BASES:
        if v1 % 2:
            return False
        if basis == "1":
            if k > 0 and v1 >= 4 and h0 > 0:
                return False  # d1(v1^(2q+1) h1^3) = h0 v1^(2q+4) k
        elif h0 > 0:
            return False
    elif basis in ("x", "y", "yh2"):
        return False
    elif basis in ("xh1", "x^2"):
        if v1 == 1 or h0 > 0:
            return False
    elif basis in ("x^2h1", "h2^2", "h2^3"):
        if h0 > 0:
            return False
    # h2 and x^3 retain all h0 levels on E2.
    if page == 2:
        return True

    # E3: d2 acts only on the exact v1^2 family. v1^6 is NOT a source:
    # its putative target v1^4 h2 is zero in the E1 algebra.
    if basis == "1" and v1 == 2:
        return False
    if basis == "h2" and h0 >= 2:
        return False
    if page == 3:
        return True

    # E4: d3(x^3)=h0^3 k, equivalently Table 1's d3(y h2^2)=h0^3 kD.
    if basis == "x^3":
        return False
    if basis == "1" and v1 == 0 and k > 0 and h0 >= 3:
        return False
    return True


def differential(monomial: BSSMonomial, page: int) -> BSSMonomial | None:
    """Return the single nonzero target basis vector, or None.

    A class absent from E_page supports no map on that page. All returned
    targets are live on E_page and both endpoints disappear on E_(page+1).
    The map is h0-, k-, and D-linear; these factors are never enumerated.
    """
    _page(page)
    if not is_live(monomial, page):
        return None
    basis, v1, k, D, h0 = monomial.as_tuple()
    if page == 1:
        if basis in FREE_BASES and v1 % 2:
            index = FREE_BASES.index(basis)
            if index < 3:
                return replace(monomial, basis=FREE_BASES[index+1], v1=v1-1, h0=h0+1)
            return BSSMonomial("1", v1=v1+3, k=k+1, D=D, h0=h0+1)
        if basis == "x":
            if v1 == 0:
                return BSSMonomial("h2^2", k=k, D=D-1, h0=h0+1)
            return BSSMonomial("xh1", k=k, D=D, h0=h0+1)
        if basis == "xh1" and v1 == 1:
            return BSSMonomial("h2^3", k=k, D=D-1, h0=h0+1)
        if basis == "x^2" and v1 == 1:
            return BSSMonomial("x^2h1", k=k, D=D, h0=h0+1)
        if basis == "y":
            return BSSMonomial("x^2", k=k, D=D, h0=h0+1)
        if basis == "yh2":
            return BSSMonomial("x^2h1", v1=1, k=k, D=D, h0=h0+1)
    elif page == 2 and basis == "1" and v1 == 2:
        return BSSMonomial("h2", k=k, D=D, h0=h0+2)
    elif page == 3 and basis == "x^3":
        return BSSMonomial("1", k=k+1, D=D, h0=h0+3)
    return None


def _ceil_div(numerator: int, denominator: int) -> int:
    return -((-numerator)//denominator)


def iter_window(stem_min: int, stem_max: int, filtration_min: int, filtration_max: int,
                *, page: int, v1_max: int, h0_max: int) -> Iterator[BSSMonomial]:
    """Enumerate live classes in an explicitly truncated display window.

    Both caps are inclusive and mandatory. They do not imply that higher
    v1/h0 classes vanish. In particular D inverses allow arbitrarily high
    v1 powers to fall inside the same finite bidegree window. The iterator
    therefore cannot promise a complete cell merely from finite bounds.
    """
    _page(page)
    for name, value in (("stem_min", stem_min), ("stem_max", stem_max)):
        _integer(value, name)
    for name, value in (("filtration_min", filtration_min), ("filtration_max", filtration_max),
                        ("v1_max", v1_max), ("h0_max", h0_max)):
        _integer(value, name, minimum=0)
    if stem_min > stem_max or filtration_min > filtration_max:
        raise ValueError("Window lower bounds must not exceed upper bounds")
    for basis, (base_stem, base_filtration) in BASIS_GRADES.items():
        max_v1 = v1_max if basis in FREE_BASES else min(v1_max, 1 if basis in V1_LENGTH_TWO_BASES else 0)
        k_min = max(0, _ceil_div(filtration_min-base_filtration, 4))
        k_max = (filtration_max-base_filtration)//4
        for k in range(k_min, k_max+1):
            for v1 in range(max_v1+1):
                shifted_stem = base_stem + 2*v1 - 4*k
                D_min = _ceil_div(stem_min-shifted_stem, 8)
                D_max = (stem_max-shifted_stem)//8
                for D in range(D_min, D_max+1):
                    for h0 in range(h0_max+1):
                        monomial = BSSMonomial(basis, v1=v1, k=k, D=D, h0=h0)
                        if is_live(monomial, page):
                            yield monomial


def enumerate_window(stem_min: int, stem_max: int, filtration_min: int, filtration_max: int,
                     *, page: int, v1_max: int, h0_max: int,
                     limit: int = 100_000) -> list[BSSMonomial]:
    """Materialize iter_window with an explicit guard against excessive output."""
    _integer(limit, "limit", minimum=1)
    result = []
    for monomial in iter_window(stem_min, stem_max, filtration_min, filtration_max,
                               page=page, v1_max=v1_max, h0_max=h0_max):
        if len(result) >= limit:
            raise ValueError("2-BSS window exceeds the requested materialization limit")
        result.append(monomial)
    return result
