"""Page products from Beaudry/Henn's mod-2 cohomology algebra.

Authority: Beaudry, Towards the homotopy of the K(2)-local Moore spectrum
at p=2, Appendix A by H.-W. Henn, Theorem A.14 and Figure A.4.
We use h1=eta, h2=nu, x_Bea=D*x, y_Bea=D^2*y, Delta=D^3.
The tables below are the products in A.14 after that explicit change of
notation, extended over F4[D^{+/-1},k,h0]. Later-page products are their
kernel/image quotients, NOT the hidden extensions of the integral abutment.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

from . import bss_integer as integer, bss_sigma as sigma


SOURCE_REF = ("Beaudry17b, Appendix A by H.-W. Henn, Theorem A.14(a-d) "
              "and Figure A.4 (PDF pp. 57, 63); "
              "eta=h1, nu=h2, x_Bea=Dx, y_Bea=D^2y, Delta=D^3")
OPERATOR_TEX = {"h0": r"h_0", "h1": r"h_1", "h2": r"h_2", "v1": r"v_1",
                "v1^2": r"v_1^2", "v1^4": r"v_1^4", "k": "k", "D": "D",
                "D^-1": r"D^{-1}", "x": "x", "y": "y"}
OPERATOR_MONOMIAL = {
    "h0": integer.BSSMonomial("1", h0=1), "h1": integer.BSSMonomial("h1"),
    "h2": integer.BSSMonomial("h2"), "v1": integer.BSSMonomial("1", v1=1),
    "v1^2": integer.BSSMonomial("1", v1=2), "v1^4": integer.BSSMonomial("1", v1=4),
    "k": integer.BSSMonomial("1", k=1), "D": integer.BSSMonomial("1", D=1),
    "D^-1": integer.BSSMonomial("1", D=-1),
    "x": integer.BSSMonomial("x"), "y": integer.BSSMonomial("y"),
}
# Target basis, additional v1 exponent, additional k exponent, additional D exponent.
# Unlisted products vanish by A.14(c,d), not by a display-window cutoff.
_PRODUCTS = {
    "h1": {"1": ("h1", 0, 0, 0), "h1": ("h1^2", 0, 0, 0),
           "h1^2": ("h1^3", 0, 0, 0), "h1^3": ("1", 4, 1, 0),
           "x": ("xh1", 0, 0, 0), "xh1": ("h2^3", 0, 0, -1),
           "x^2": ("x^2h1", 0, 0, 0), "y": ("x^2", 1, 0, 0)},
    "h2": {"1": ("h2", 0, 0, 0), "x": ("xh1", 1, 0, 0),
           "x^2": ("x^2h1", 1, 0, 0), "h2": ("h2^2", 0, 0, 0),
           "y": ("yh2", 0, 0, 0), "h2^2": ("h2^3", 0, 0, 0),
           "yh2": ("x^3", 0, 0, 1)},
    "x": {"1": ("x", 0, 0, 0), "h1": ("xh1", 0, 0, 0),
          "h1^2": ("h2^3", 0, 0, -1), "x": ("x^2", 0, 0, 0),
          "xh1": ("x^2h1", 0, 0, 0), "x^2": ("x^3", 0, 0, 0),
          "h2": ("xh1", 1, 0, 0)},
    "y": {"1": ("y", 0, 0, 0), "h1": ("x^2", 1, 0, 0),
          "h1^2": ("x^2h1", 1, 0, 0), "h2": ("yh2", 0, 0, 0),
          "y": ("h2^2", 0, 0, -1), "h2^2": ("x^3", 0, 0, 1),
          "yh2": ("h2^3", 0, 0, -1)},
}


def chart_operators(page: int) -> tuple[str, ...]:
    integer._page(page)
    # A.4 includes x_Bea and y_Bea lines as well. Here the explicitly
    # normalized x=D^-1*x_Bea and y=D^-2*y_Bea both have degree (-1,1).
    # They cease to be multipliers on E2, since neither is a d1 cycle.
    return (("h0", "h1", "h2", "v1", "x", "y") if page == 1 else
            ("h0", "h1", "h2", "v1^2" if page == 2 else "v1^4"))


def raw_product(monomial: integer.BSSMonomial, operator: str) -> tuple[integer.BSSMonomial, ...]:
    """An E1 product; a noncycle multiplier is still an E1 algebra element."""
    if operator not in OPERATOR_MONOMIAL:
        raise ValueError("Unknown 2-BSS multiplier")
    if operator in ("h0", "k", "D", "D^-1"):
        field, step = {"h0": ("h0", 1), "k": ("k", 1), "D": ("D", 1), "D^-1": ("D", -1)}[operator]
        return (replace(monomial, **{field: getattr(monomial, field) + step}),)
    if operator.startswith("v1"):
        name, v, k, d = monomial.basis, {"v1": 1, "v1^2": 2, "v1^4": 4}[operator], 0, 0
    else:
        spec = _PRODUCTS[operator].get(monomial.basis)
        if spec is None:
            return ()
        name, v, k, d = spec
    exponent = monomial.v1 + v
    if ((name in integer.V1_LENGTH_TWO_BASES and exponent >= 2)
            or (name in integer.V1_LENGTH_ONE_BASES and exponent >= 1)):
        return ()
    return (integer.BSSMonomial(name, v1=exponent, k=monomial.k+k,
                                D=monomial.D+d, h0=monomial.h0),)


@lru_cache(maxsize=32768)
def multiply(monomial, operator: str, page: int, sector: str = "integer") -> tuple:
    """Exact current-page product, in the page's computational basis.

    An absent source or multiplier is an error, never a claim that its
    product is zero. A valid product may be zero or a genuine basis sum.
    """
    integer._page(page)
    if sector not in ("integer", "sigma"):
        raise ValueError("Unknown 2-BSS sector")
    engine = integer if sector == "integer" else sigma
    if not engine.is_live(monomial, page):
        raise ValueError("Source is absent from this 2-BSS page")
    if operator not in OPERATOR_MONOMIAL:
        raise ValueError("Unknown 2-BSS multiplier")
    if not integer.is_live(OPERATOR_MONOMIAL[operator], page):
        raise ValueError("Multiplier is absent from this 2-BSS page")
    inputs = (monomial,) if sector == "integer" else sigma.to_integer_basis(monomial)
    raw = sigma._xor(term for item in inputs for term in raw_product(item, operator))
    if sector == "sigma":
        return sigma.reduce_e1_vector(raw, page)
    terms = raw
    for previous in range(1, min(page, 4)):
        if any(integer.differential(term, previous) is not None for term in terms):
            raise AssertionError("Product of page classes is not a previous-page cycle")
        terms = tuple(term for term in terms if integer.is_live(term, previous+1))
    return terms


def differential_preimages(target, page: int, sector: str) -> tuple:
    """All coordinate sources hitting target, independent of view/caps.

    Every adapted column has one coordinate target. Invert the finite
    coefficient shifts and confirm against the actual differential; no
    unbounded predecessor search or heuristic name matching is involved.
    """
    engine = integer if sector == "integer" else sigma
    if target.h0 < page:
        return ()
    names = integer.BASIS_GRADES if sector == "integer" else sigma.BASIS_SPECS
    cls = integer.BSSMonomial if sector == "integer" else sigma.SigmaMonomial
    candidates = set()
    for name in names:
        for v in {0, 1, 2, target.v1 + 1, target.v1 - 3}:
            if v < 0:
                continue
            for k in {target.k, target.k-1}:
                if k < 0:
                    continue
                for d in {target.D, target.D+1}:
                    try:
                        source = cls(name, v1=v, k=k, D=d, h0=target.h0-page)
                    except ValueError:
                        continue
                    if engine.differential(source, page) == target:
                        candidates.add(source)
    return tuple(sorted(candidates, key=lambda item: item.as_tuple()))
