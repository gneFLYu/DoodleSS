"""Exact (*-sigma_i) auxiliary 2-BSS in a differential-adapted additive basis.

The E1 multiplication authority is Beaudry17b Appendix A by H.-W. Henn,
Theorems A.14/A.20, with the normalized x,y dictionary in bss_integer.
That appendix does not compute this RO-graded twist. The coefficients,
h0 grading and group-cohomology coordinates are as in bss_integer.
The published twisted differential is DKLLW24 Proposition 3.6: tensoring
with the mod-2 orientation u_sigma_i changes d1 to
d1(a*u) = d1(a)*u + h0*a*(x+y)*u. Identifying the twist with x+y is
additional coefficient-module input, not a consequence of A.14 alone.

An invertible, explicitly recorded basis change makes every nonzero d1
column a different coordinate target. On E2 the only d2 source family is
x*h1^2*u, with target h0^2*v1^2*k*u. The other degree-(1,3) representative
is {x*h1^2+x^2*h1*v1}*u, an h0-torsion cycle. This implements Proposition
3.8 compatibly with the d1 quotient, instead of assigning inconsistent d2
values to the equal positive-h0 classes x*h1^2*u and x^2*h1*v1*u.

This higher map is forced on the two raw representatives: their difference
is annihilated by h0 on E2, whereas multiplication by h0 is injective on
the possible target family h0^2*v1^2*k*u. Thus their d2 values agree. All
other filtration-two/three E2 rows are h0-torsion, so cannot map to those
h0-free targets; filtration-zero rows have no surviving target at the
required positive h0 level. After d2, no target remains at h0 level >=3
in positive cohomological filtration, which also rules out higher maps.

All vectors below carry u_sigma_i, whose actual degree is 1-sigma_i and
whose dimension-adjusted plotted degree is (0,0). E3=E-infinity for this
auxiliary sequence (DKLLW24 Table 4 and Theorem 3.10); its d2 is not
an undetermined differential, nor is it asserted to be proved in
Beaudry's paper. Hidden extensions
are not substituted into its E1 algebra or mistaken for HFPSS permanence.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, Iterator

from .bss_integer import BSSMonomial, differential as integer_differential


@dataclass(frozen=True, slots=True)
class SigmaBasisSpec:
    expression_tex: str
    stem: int
    filtration: int
    max_v1: int | None
    # Each raw summand is (integer E1 basis, extra v1 exponent, extra D exponent).
    raw_terms: tuple[tuple[str, int, int], ...]


# Keys are explicit expressions, not anonymous replacement names. The TeX
# metadata respects the user-facing x/y, h1, h2, v1, k, D, orientation order.
BASIS_SPECS: dict[str, SigmaBasisSpec] = {
    "1": SigmaBasisSpec("1", 0, 0, None, (("1", 0, 0),)),
    "h1": SigmaBasisSpec(r"h_1", 1, 1, None, (("h1", 0, 0),)),
    "{h1^2+v1xh1}": SigmaBasisSpec(r"\{h_1^2+xh_1v_1\}", 2, 2, None,
                                  (("h1^2", 0, 0), ("xh1", 1, 0))),
    "h1^3": SigmaBasisSpec(r"h_1^3", 3, 3, None, (("h1^3", 0, 0),)),
    "x": SigmaBasisSpec("x", -1, 1, 0, (("x", 0, 0),)),
    "{h1+v1x}": SigmaBasisSpec(r"\{h_1+xv_1\}", 1, 1, 0, (("h1", 0, 0), ("x", 1, 0))),
    "xh1": SigmaBasisSpec(r"xh_1", 0, 2, 1, (("xh1", 0, 0),)),
    "x^2": SigmaBasisSpec("x^2", -2, 2, 0, (("x^2", 0, 0),)),
    "{xh1+v1x^2}": SigmaBasisSpec(r"\{xh_1+x^2v_1\}", 0, 2, 0,
                                 (("xh1", 0, 0), ("x^2", 1, 0))),
    "x^2h1": SigmaBasisSpec(r"x^2h_1", -1, 3, 0, (("x^2h1", 0, 0),)),
    "{xh1^2+v1x^2h1}": SigmaBasisSpec(r"\{xh_1^2+x^2h_1v_1\}", 1, 3, 0,
                                      (("h2^3", 0, -1), ("x^2h1", 1, 0))),
    "h2": SigmaBasisSpec(r"h_2", 3, 1, 0, (("h2", 0, 0),)),
    "{x+y}": SigmaBasisSpec(r"\{x+y\}", -1, 1, 0, (("x", 0, 0), ("y", 0, 0))),
    "{x^2+y^2}": SigmaBasisSpec(r"\{x^2+y^2\}", -2, 2, 0,
                               (("x^2", 0, 0), ("h2^2", 0, -1))),
    "{v1xh1+yh2}": SigmaBasisSpec(r"\{xh_1v_1+yh_2\}", 2, 2, 0,
                                  (("xh1", 1, 0), ("yh2", 0, 0))),
    "xh1^2": SigmaBasisSpec(r"xh_1^2", 1, 3, 0, (("h2^3", 0, -1),)),
    "x^3": SigmaBasisSpec("x^3", -3, 3, 0, (("x^3", 0, 0),)),
}
FREE_BASES = ("1", "h1", "{h1^2+v1xh1}", "h1^3")
SOURCE_REFS = (
    "Beaudry17b, Appendix A by H.-W. Henn, Theorems A.14 and A.20 (PDF pp. 57, 61-62): primary E1 multiplication, under x_Bea=Dx and y_Bea=D^2y; not an RO-graded Bockstein computation",
    "DKLLW24, Section 3.2, Propositions 3.6 and 3.8, Table 4 and Theorem 3.10 (journal PDF pp. 22-24): published sigma twist, d2, and abutment; attribution is separate from Beaudry/Henn's E1 algebra",
)


def _integer(value: int, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _power_tex(symbol: str, exponent: int) -> str:
    return "" if exponent == 0 else symbol if exponent == 1 else rf"{symbol}^{{{exponent}}}"


@dataclass(frozen=True, slots=True)
class SigmaMonomial:
    """An adapted E1 basis vector times v1^v1 k^k D^D h0^h0 u_sigma_i.

    Unlike the raw integer basis, several labels denote explicit sums. The
    canonical v1 parameter is an *extra* exponent, not a bound on the v1
    powers already occurring inside a named representative.
    """

    basis: str
    v1: int = 0
    k: int = 0
    D: int = 0
    h0: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.basis, str) or self.basis not in BASIS_SPECS:
            raise ValueError("Unknown adapted sigma 2-BSS basis expression")
        for name in ("v1", "k", "h0"):
            _integer(getattr(self, name), name, minimum=0)
        _integer(self.D, "D")
        maximum = BASIS_SPECS[self.basis].max_v1
        if maximum is not None and self.v1 > maximum:
            raise ValueError("The extra v1 exponent is outside this adapted basis family")

    def as_tuple(self) -> tuple[str, int, int, int, int]:
        return self.basis, self.v1, self.k, self.D, self.h0

    @property
    def bidegree(self) -> tuple[int, int]:
        spec = BASIS_SPECS[self.basis]
        return spec.stem+2*self.v1-4*self.k+8*self.D, spec.filtration+4*self.k

    @property
    def tridegree(self) -> tuple[int, int, int]:
        return *self.bidegree, self.h0

    @property
    def label_tex(self) -> str:
        expression = BASIS_SPECS[self.basis].expression_tex
        if self.basis == "{h1^2+v1xh1}" and self.v1:
            # The other summand contains v1^2*x and is zero already on E1.
            expression = r"h_1^2"
        if expression == "1":
            expression = ""
        return (_power_tex("h_0", self.h0) + expression + _power_tex("v_1", self.v1)
                + _power_tex("k", self.k) + _power_tex("D", self.D) + r"u_{\sigma_i}")


def _xor(terms: Iterable) -> tuple:
    """Canonical coefficient-one sum over characteristic two."""
    result = set()
    for term in terms:
        if term in result:
            result.remove(term)
        else:
            result.add(term)
    return tuple(sorted(result, key=lambda term: term.as_tuple()))


def to_integer_basis(monomial: SigmaMonomial) -> tuple[BSSMonomial, ...]:
    """Expand the true E1 vector (with the common u_sigma_i factor implicit)."""
    if not isinstance(monomial, SigmaMonomial):
        raise TypeError("monomial must be a SigmaMonomial")
    terms = []
    for basis, extra_v1, extra_D in BASIS_SPECS[monomial.basis].raw_terms:
        v1 = monomial.v1+extra_v1
        # The only unbounded sum family is h1^2+v1*xh1, and v1^2*xh1=0.
        if basis == "xh1" and v1 >= 2:
            continue
        terms.append(BSSMonomial(basis, v1=v1, k=monomial.k, D=monomial.D+extra_D, h0=monomial.h0))
    return _xor(terms)


def from_integer_basis(terms: Iterable[BSSMonomial]) -> tuple[SigmaMonomial, ...]:
    """Invert the E1 basis change on a coefficient-one raw vector.

    The matrix and its inverse have coefficients in F2, so this conversion
    extends F4-linearly. This helper's iterable syntax represents sums with
    coefficient one; an F4 client may apply it separately to scalar terms.
    """
    result = []
    for raw in terms:
        if not isinstance(raw, BSSMonomial):
            raise TypeError("Raw terms must be integer E1 BSSMonomial objects")
        basis, v1, k, D, h0 = raw.as_tuple()

        def add(name: str, exponent: int = 0, D_shift: int = 0) -> None:
            result.append(SigmaMonomial(name, v1=exponent, k=k, D=D+D_shift, h0=h0))

        if basis in ("1", "h1", "h1^3", "xh1"):
            add(basis, v1)
        elif basis == "h1^2":
            add("{h1^2+v1xh1}", v1)
            if v1 == 0:
                add("xh1", 1)
        elif basis == "x":
            if v1:
                add("{h1+v1x}")
                add("h1")
            else:
                add("x")
        elif basis == "x^2":
            if v1:
                add("{xh1+v1x^2}")
                add("xh1")
            else:
                add("x^2")
        elif basis == "x^2h1":
            if v1:
                add("{xh1^2+v1x^2h1}")
                add("xh1^2")
            else:
                add("x^2h1")
        elif basis in ("h2", "x^3"):
            add(basis)
        elif basis == "y":
            add("{x+y}")
            add("x")
        elif basis == "h2^2":
            add("{x^2+y^2}", D_shift=1)
            add("x^2", D_shift=1)
        elif basis == "yh2":
            add("{v1xh1+yh2}")
            add("xh1", 1)
        elif basis == "h2^3":
            add("xh1^2", D_shift=1)
    return _xor(result)


def _multiply_x_plus_y(raw: BSSMonomial) -> tuple[BSSMonomial, ...]:
    """Multiplication in the original E1 algebra, reduced by Proposition 3.2."""
    basis, v1, k, D, h0 = raw.as_tuple()
    specs: list[tuple[str, int, int]] = []
    if basis == "1":
        if v1 == 0:
            specs = [("x", 0, 0), ("y", 0, 0)]
        elif v1 == 1:
            specs = [("x", 1, 0)]
    elif basis == "h1":
        if v1 == 0:
            specs = [("xh1", 0, 0), ("x^2", 1, 0)]
        elif v1 == 1:
            specs = [("xh1", 1, 0)]
    elif basis == "h1^2" and v1 == 0:
        specs = [("h2^3", 0, -1), ("x^2h1", 1, 0)]
    elif basis == "x":
        specs = [("x^2", v1, 0)]
    elif basis == "xh1":
        specs = [("x^2h1", v1, 0)]
    elif basis == "x^2" and v1 == 0:
        specs = [("x^3", 0, 0)]
    elif basis == "h2":
        specs = [("xh1", 1, 0), ("yh2", 0, 0)]
    elif basis == "y":
        specs = [("h2^2", 0, -1)]
    elif basis == "h2^2":
        specs = [("x^3", 0, 1)]
    elif basis == "yh2":
        specs = [("h2^3", 0, -1)]
    return tuple(BSSMonomial(name, v1=v, k=k, D=D+d, h0=h0) for name, v, d in specs)


def raw_twisted_d1(terms: Iterable[BSSMonomial]) -> tuple[BSSMonomial, ...]:
    """Independently evaluate d1(a)+h0*a*(x+y), prior to the basis change."""
    result = []
    for term in terms:
        target = integer_differential(term, 1)
        if target is not None:
            result.append(target)
        result.extend(replace(product, h0=product.h0+1) for product in _multiply_x_plus_y(term))
    return _xor(result)


def is_live(monomial: SigmaMonomial, page: int) -> bool:
    """Nonzero adapted coordinate on E_page; E3 and subsequent pages coincide."""
    _integer(page, "page", minimum=1)
    if not isinstance(monomial, SigmaMonomial):
        raise TypeError("monomial must be a SigmaMonomial")
    if page == 1:
        return True
    basis, v1, k, _, h0 = monomial.as_tuple()
    if basis in FREE_BASES:
        if v1 % 2:
            return False
        if basis == "1":
            if v1 == 0 or (k > 0 and v1 >= 4 and h0 > 0):
                return False
        elif basis == "h1" and v1 == 0:
            return False
        elif h0 > 0:
            return False
    elif basis in ("x", "xh1", "x^2", "h2"):
        return False
    elif basis != "xh1^2" and h0 > 0:
        return False
    if page == 2:
        return True
    if basis == "xh1^2":
        return False
    if basis == "1" and v1 == 2 and k > 0 and h0 >= 2:
        return False
    return True


def differential(monomial: SigmaMonomial, page: int) -> SigmaMonomial | None:
    """The single nonzero adapted target; absent sources have no page map."""
    _integer(page, "page", minimum=1)
    if not is_live(monomial, page):
        return None
    basis, v1, k, D, h0 = monomial.as_tuple()

    def target(name: str, exponent: int = 0, extra_k: int = 0, length: int = 1) -> SigmaMonomial:
        return SigmaMonomial(name, v1=exponent, k=k+extra_k, D=D, h0=h0+length)

    if page == 1:
        if basis == "1":
            if v1 == 0:
                return target("{x+y}")
            if v1 == 1:
                return target("{h1+v1x}")
            if v1 % 2:
                return target("h1", v1-1)
        elif basis == "h1":
            if v1 == 0:
                return target("{xh1+v1x^2}")
            if v1 % 2:
                return target("{h1^2+v1xh1}", v1-1)
        elif basis == "{h1^2+v1xh1}" and v1 % 2:
            return target("h1^3", v1-1)
        elif basis == "h1^3" and v1 % 2:
            return target("1", v1+3, extra_k=1)
        elif basis == "x":
            return target("{x^2+y^2}")
        elif basis == "xh1":
            return target("x^2h1" if v1 == 0 else "{xh1^2+v1x^2h1}")
        elif basis == "x^2":
            return target("x^3")
        elif basis == "h2":
            return target("{v1xh1+yh2}")
    elif page == 2 and basis == "xh1^2":
        return target("1", exponent=2, extra_k=1, length=2)
    return None


def reduce_e1_vector(terms: Iterable[BSSMonomial], page: int) -> tuple[SigmaMonomial, ...]:
    """Project a raw cycle to E_page, rejecting a vector that is not a cycle.

    Incoming boundary coordinates are discarded only after checking the
    outgoing coordinates. Merely being absent from a later page is not
    permission to silently turn a non-cycle into zero.
    """
    _integer(page, "page", minimum=1)
    result = from_integer_basis(terms)
    for previous_page in range(1, min(page, 3)):
        if any(differential(term, previous_page) is not None for term in result):
            raise ValueError(f"The vector is not an E{previous_page+1} cycle")
        result = tuple(term for term in result if is_live(term, previous_page+1))
    return result


def differential_e1_vector(terms: Iterable[BSSMonomial], page: int) -> tuple[SigmaMonomial, ...]:
    """Evaluate a valid raw representative's page differential in adapted coordinates."""
    return _xor(target for term in reduce_e1_vector(terms, page)
                if (target := differential(term, page)) is not None)


def iter_window(stem_min: int, stem_max: int, filtration_min: int, filtration_max: int,
                *, page: int, v1_max: int, h0_max: int) -> Iterator[SigmaMonomial]:
    """Finite display enumeration with mandatory extra-v1 and h0 caps.

    The named basis expressions can already contain v1, irrespective of
    the extra-v1 cap. Bounds and caps never enter is_live/differential.
    """
    _integer(page, "page", minimum=1)
    for name, value in (("stem_min", stem_min), ("stem_max", stem_max)):
        _integer(value, name)
    for name, value in (("filtration_min", filtration_min), ("filtration_max", filtration_max),
                        ("v1_max", v1_max), ("h0_max", h0_max)):
        _integer(value, name, minimum=0)
    if stem_min > stem_max or filtration_min > filtration_max:
        raise ValueError("Window lower bounds must not exceed upper bounds")
    for basis, spec in BASIS_SPECS.items():
        maximum = v1_max if spec.max_v1 is None else min(v1_max, spec.max_v1)
        k_min = max(0, -((spec.filtration-filtration_min)//4))
        k_max = (filtration_max-spec.filtration)//4
        for k in range(k_min, k_max+1):
            for v1 in range(maximum+1):
                stem = spec.stem+2*v1-4*k
                D_min, D_max = -((stem-stem_min)//8), (stem_max-stem)//8
                for D in range(D_min, D_max+1):
                    for h0 in range(h0_max+1):
                        term = SigmaMonomial(basis, v1=v1, k=k, D=D, h0=h0)
                        if is_live(term, page):
                            yield term


def enumerate_window(stem_min: int, stem_max: int, filtration_min: int, filtration_max: int,
                     *, page: int, v1_max: int, h0_max: int,
                     limit: int = 100_000) -> list[SigmaMonomial]:
    _integer(limit, "limit", minimum=1)
    result = []
    for term in iter_window(stem_min, stem_max, filtration_min, filtration_max,
                            page=page, v1_max=v1_max, h0_max=h0_max):
        if len(result) >= limit:
            raise ValueError("Sigma 2-BSS window exceeds the materialization limit")
        result.append(term)
    return result
