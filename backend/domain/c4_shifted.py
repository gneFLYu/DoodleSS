"""Exact additive C4/C4 HFPSS pages in the 1-sigma slice.

Every term below includes BBHS's mathfrak p, of actual degree -3-sigma
(integer coordinate -4 relative to 1-sigma). It is an E2 unit, NOT a
permanent cycle. In particular d3(M p) has the extra term
M eta varpi Delta_1^-1 p; the integer page quotient cannot be reused.

Sources: BBHS20 Props. 5.10, 5.21, 5.24, 5.27, 5.28; Remarks 5.19-5.20;
Cor. 5.26. The nine shifted seeds, their stated linearities, and Leibniz
determine these maps. At low filtration the nonzero printed products force
three additional source families: d11(varsigma Delta p), d13(nu Delta^2 p),
and d13(2 Delta^4 p). Multiplication by kappa-bar is injective on their
one-dimensional target lines; it is NOT inverted as a general period.
Only associated-graded C4/C4 groups are computed,
not Mackey functors or hidden extensions. Completed coefficients are
retained as ideals, never replaced by a finite set of scalar ports.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Iterator

from .c4_integer import (
    DIFFERENTIAL_PAGES, FAMILIES, Term as IntegerTerm,
    e2_nonzero, normalize_monomial as _normalize_integer, multiply_e2,
)


SOURCE = "BBHS20, Props. 5.10, 5.21, 5.24, 5.27-5.28; Cor. 5.26; shifted 1-sigma slice"


def _integer(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _page(page: int) -> int:
    _integer(page, "page")
    if not 2 <= page <= 14:
        raise ValueError("The computed shifted C4 pages are E2 through E14")
    return page


@dataclass(frozen=True)
class Term(IntegerTerm):
    """The inherited factors, multiplied by p exactly once."""

    @property
    def stem(self) -> int:
        return super().stem - 4

    def tex(self) -> str:
        prefix = super().tex()
        return (prefix + " " if prefix != "1" else "") + r"\mathfrak p"


def normalize_monomial(*, eta=0, nu=0, varsigma=0, varpi=0, t2=0,
                       delta=0, mu=0, two=0) -> Term | None:
    """E2 ring normalization, followed by p; this does not transport pages."""
    result = _normalize_integer(eta=eta, nu=nu, varsigma=varsigma, varpi=varpi,
                                t2=t2, delta=delta, mu=mu, two=two)
    return None if result is None else Term(**asdict(result))


def _raw_differential(term: Term, page: int) -> Term | None:
    family, q, d, n, a = term.family, term.q, term.d, term.mu, term.two
    if page == 3:
        if a:
            return None
        # The p connection reverses the integer q-parities; T2's two
        # terms cancel by T2*eta = mu*varsigma.
        if family == "one":
            return Term("eta", 1, d - 1, n)
        if family == "eta" and q % 2 == 0:
            return Term("eta2", q + 1, d - 1, n)
        if family == "varsigma" and q % 2:
            return Term("varpi", q + 2, d - 1, n + 1)
        if family == "varpi" and q % 2 == 0:
            return Term("eta", q + 1, d - 1, n)
        if family == "eta2" and q % 2 == 0:
            return Term("varsigma", q + 2, d - 2, n + 1)
    if n:
        return None
    if page == 5 and a == 0:
        if family == "nu" and (d - q // 2) % 2:
            return Term("varpi", q + 3, d - 2, two=1)
        if family == "varpi" and q % 2 and (d - (q - 1) // 2) % 2:
            return Term("nu", q + 2, d - 2)
    if page == 7 and family == "varpi" and q % 2:
        c = d - (q - 1) // 2
        # Odd residues both occur: multiply the printed 2 Delta^3 varpi p
        # differential by Delta^2 and use Leibniz. Delta^2 is not a unit
        # period on E8, so no later-page Delta^2 periodicity is inferred.
        if (c % 2 and a == 1) or (c % 4 == 0 and a == 0):
            return Term("varsigma", q + 3, d - 3)
    if page == 11 and family == "varsigma" and q % 2 == 0 and a == 0:
        if (d - q // 2) % 4 == 1:
            return Term("varpi", q + 6, d - 4, two=1)
    if page == 13 and q % 2 == 0:
        c = (d - q // 2) % 4
        if family == "nu" and a == 0 and c == 2:
            return Term("varpi", q + 7, d - 5)
        if family in ("one", "varpi") and a == 1 and c == 0:
            return Term("nu", q + 6, d - 5)
    return None


def _preimage_candidates(term: Term, page: int) -> tuple[Term, ...]:
    family, q, d, n, a = term.family, term.q, term.d, term.mu, term.two
    candidates = []
    if page == 3 and a == 0:
        if family == "eta":
            if q == 1:
                candidates.append(Term("one", d=d + 1, mu=n))
            elif q >= 3:
                candidates.append(Term("varpi", q - 1, d + 1, n))
        if family == "eta2" and q >= 1:
            candidates.append(Term("eta", q - 1, d + 1, n))
        if family == "varpi" and q >= 3 and n:
            candidates.append(Term("varsigma", q - 2, d + 1, n - 1))
        if family == "varsigma" and q >= 2 and n:
            candidates.append(Term("eta2", q - 2, d + 2, n - 1))
    if n:
        return tuple(candidates)
    if page == 5:
        if family == "varpi" and q >= 3 and a == 1:
            candidates.append(Term("nu", q - 3, d + 2))
        if family == "nu" and q >= 3 and a == 0:
            candidates.append(Term("varpi", q - 2, d + 2))
    if page == 7 and family == "varsigma" and q >= 4 and a == 0:
        candidates.extend(Term("varpi", q - 3, d + 3, two=v) for v in (0, 1))
    if page == 11 and family == "varpi" and q >= 6 and a == 1:
        candidates.append(Term("varsigma", q - 6, d + 4))
    if page == 13:
        if family == "varpi" and q >= 7 and a == 0:
            candidates.append(Term("nu", q - 7, d + 5))
        if family == "nu" and a == 0:
            if q == 6:
                candidates.append(Term("one", d=d + 5, two=1))
            elif q >= 7:
                candidates.append(Term("varpi", q - 6, d + 5, two=1))
    return tuple(candidates)


@lru_cache(maxsize=200_000)
def is_live(term: Term, page: int = 2) -> bool:
    _page(page)
    if not e2_nonzero(term):
        return False
    for r in DIFFERENTIAL_PAGES:
        if r >= page:
            break
        if _raw_differential(term, r) is not None:
            return False
        if any(is_live(source, r) and _raw_differential(source, r) == term
               for source in _preimage_candidates(term, r)):
            return False
    return True


def differential(term: Term, page: int) -> Term | None:
    _page(page)
    if page not in DIFFERENTIAL_PAGES or not is_live(term, page):
        return None
    target = _raw_differential(term, page)
    if target is not None and not is_live(target, page):
        raise ArithmeticError(f"Shifted C4 map targets absent E{page} term: {term} -> {target}")
    return target


def incoming(term: Term, page: int) -> tuple[Term, ...]:
    _page(page)
    if page not in DIFFERENTIAL_PAGES or not is_live(term, page):
        return ()
    return tuple(source for source in _preimage_candidates(term, page)
                 if is_live(source, page) and _raw_differential(source, page) == term)


def multiply(term: Term, multiplier: str, page: int = 2) -> Term | None:
    """Multiply a shifted class, then use this slice's own page quotient."""
    _page(page)
    if multiplier not in ("eta", "nu", "2"):
        raise ValueError("C4 chart multipliers are eta, nu, and 2")
    if not is_live(term, page):
        return None
    result = multiply_e2(term, multiplier)
    shifted = None if result is None else Term(**asdict(result))
    return shifted if shifted is not None and is_live(shifted, page) else None


def module_descriptor(family: str, q: int, d: int, page: int = 2) -> dict:
    _page(page)
    base = Term(family, q, d)
    branches = []
    for mu in (0, 1):
        valuations = [a for a in range(5) if is_live(Term(family, q, d, mu, a), page)]
        if not valuations:
            continue
        unbounded = family in ("one", "T2") and 4 in valuations
        lower, upper = min(valuations), None if unbounded else max(valuations)
        representative = Term(family, q, d, mu, lower)
        branches.append({
            "mu_min": mu, "mu_max": 0 if mu == 0 else None,
            "two_min": lower, "two_max": upper,
            "completed_mu_tail": mu == 1,
            "representative": asdict(representative),
            "representative_tex": representative.tex(),
            "coefficient_description": "W(k)" if upper is None else f"2^{lower}W(k)/2^{upper+1}",
        })
    return {
        "family": family, "q": q, "d": d, "page": page,
        "stem": base.stem, "filtration": base.filtration, "label": base.tex(),
        "branches": branches, "nonzero": bool(branches),
        "base_ring": "W(k)[[mu]]", "scalar_ports_are_not_module_basis": True,
        "scope": "1-sigma C4/C4 associated-graded HFPSS; no hidden extensions",
        "source_ref": SOURCE,
    }


def differential_components(family: str, q: int, d: int, page: int) -> list[dict]:
    result = []
    for branch in module_descriptor(family, q, d, page)["branches"]:
        source = Term(**branch["representative"])
        target = differential(source, page)
        if target is None:
            continue
        result.append({
            "page": page, "source": asdict(source), "target": asdict(target),
            "source_tex": source.tex(), "target_tex": target.tex(),
            "source_branch": branch, "mu_exponent_shift": target.mu - source.mu,
            "coefficient_map": "W(k)-linear, reduction modulo 2 of the displayed source generator",
            "kernel_two_min": source.two + 1, "source_ref": SOURCE,
        })
    return result


def cells_in_window(*, page: int, stem_min: int, stem_max: int,
                    filtration_min: int = 0, filtration_max: int = 20) -> Iterator[dict]:
    _page(page)
    for name, value in (("stem_min", stem_min), ("stem_max", stem_max),
                        ("filtration_min", filtration_min), ("filtration_max", filtration_max)):
        _integer(value, name)
    if stem_min > stem_max or filtration_min < 0 or filtration_min > filtration_max:
        raise ValueError("Invalid shifted C4 chart window")
    if (stem_max - stem_min + 1) * (filtration_max - filtration_min + 1) > 250_000:
        raise ValueError("C4 chart window is too large")
    for s in range(filtration_min, filtration_max + 1):
        if s == 0:
            families = (("one", 0), ("T2", 0))
        elif s % 2:
            families = tuple((f, (s - 1) // 2) for f in ("eta", "nu", "varsigma"))
        else:
            families = (("varpi", s // 2), ("eta2", (s - 2) // 2))
        for family, q in families:
            offset = Term(family, q).stem
            first, last = (stem_min - offset + 7) // 8, (stem_max - offset) // 8
            for d in range(first, last + 1):
                cell = module_descriptor(family, q, d, page)
                if cell["nonzero"]:
                    yield cell
