"""Exact additive pages of the integer C4/C4 height-two HFPSS.

The basis is over completed Witt coefficients, not over a finite F4 vector
space. A Term specifies one coefficient monomial 2^a mu^n M Delta_1^d.
Page modules are described by a constant branch and a completed positive-mu
tail. Their scalar ports are NOT independent generators of W(k)[[mu]].

Sources: BBHS20 Proposition 5.10 and Remark 5.13 (E2), Propositions 5.21,
5.24, 5.27, 5.28 (differentials); Props. 4.4--4.7 (RO periods). The formulas
are normalized using that ring and the printed linearities. This computes
associated-graded C4/C4 groups only: no shifted-page, Mackey, or hidden-
extension computation is asserted here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Iterator


DIFFERENTIAL_PAGES = (3, 5, 7, 11, 13)
FAMILIES = ("one", "T2", "eta", "nu", "varsigma", "varpi", "eta2")
SOURCE = "BBHS20, Props. 5.10, 5.21, 5.24, 5.27-5.28; Remark 5.13"


def _integer(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    return value


def _page(page: int) -> int:
    _integer(page, "page")
    if not 2 <= page <= 14:
        raise ValueError("The computed integer C4 pages are E2 through E14")
    return page


@dataclass(frozen=True)
class Term:
    family: str
    q: int = 0
    d: int = 0
    mu: int = 0
    two: int = 0

    def __post_init__(self):
        if self.family not in FAMILIES:
            raise ValueError(f"Unknown C4 basis family {self.family!r}")
        for field in ("q", "d", "mu", "two"):
            _integer(getattr(self, field), field)
        if min(self.q, self.mu, self.two) < 0:
            raise ValueError("q, mu exponent, and 2-valuation must be nonnegative")
        if self.family in ("one", "T2") and self.q:
            raise ValueError("Filtration-zero families have q=0")
        if self.family == "varpi" and not self.q:
            raise ValueError("Use family 'one' for varpi^0")

    @property
    def filtration(self) -> int:
        if self.family in ("one", "T2"):
            return 0
        return 2 * self.q + (2 if self.family == "eta2" else 0 if self.family == "varpi" else 1)

    @property
    def stem(self) -> int:
        base = {"one": 0, "T2": 4, "eta": 1, "nu": 3, "varsigma": 5, "varpi": 0, "eta2": 2}[self.family]
        return base + 6 * self.q + 8 * self.d

    def tex(self) -> str:
        pieces = [str(2 ** self.two)] if self.two else []
        if self.mu:
            pieces.append(r"\mu" if self.mu == 1 else rf"\mu^{{{self.mu}}}")
        name = {"one": "", "T2": "T_2", "eta": r"\eta", "nu": r"\nu",
                "varsigma": r"\varsigma", "varpi": "", "eta2": r"\eta^2"}[self.family]
        if name:
            pieces.append(name)
        if self.q:
            pieces.append(r"\varpi" if self.q == 1 else rf"\varpi^{{{self.q}}}")
        if self.d:
            pieces.append(r"\Delta_1" if self.d == 1 else rf"\Delta_1^{{{self.d}}}")
        return " ".join(pieces) or "1"


def e2_nonzero(term: Term) -> bool:
    if term.family in ("one", "T2"):
        return True
    if term.family == "varpi":
        return term.two < 2 and (not term.mu or term.two == 0)
    if term.family == "nu":
        return term.two == 0 and term.mu == 0
    return term.two == 0


def normalize_monomial(*, eta=0, nu=0, varsigma=0, varpi=0, t2=0,
                       delta=0, mu=0, two=0) -> Term | None:
    """Normalize a single E2 monomial when it remains a monomial.

    T2^2 is intentionally rejected: it equals Delta_1(mu^2-4mu+8), an
    additive polynomial, and may not be silently replaced by a single port.
    None denotes zero. This covers every literal integer BBHS seed.
    """
    for key, value in locals().copy().items():
        _integer(value, key)
        if key != "delta" and value < 0:
            raise ValueError(f"{key} must be nonnegative")
    if nu and (mu or eta or varsigma or t2 or two or nu >= 3):
        return None
    if nu == 2:
        nu, varpi, two = 0, varpi + 1, two + 1
    while True:
        if eta and varsigma:
            eta, varsigma, mu, varpi = eta - 1, varsigma - 1, mu + 1, varpi + 1
        elif varsigma >= 2:
            varsigma, eta, delta = varsigma - 2, eta + 2, delta + 1
        elif eta >= 3:
            eta, varsigma, mu, varpi, delta = eta - 3, varsigma + 1, mu + 1, varpi + 1, delta - 1
        elif t2 and eta:
            t2, eta, mu, varsigma = t2 - 1, eta - 1, mu + 1, varsigma + 1
        elif t2 and varsigma:
            t2, varsigma, mu, eta, delta = t2 - 1, varsigma - 1, mu + 1, eta + 1, delta + 1
        elif t2 and varpi:
            t2, varpi, eta, delta = t2 - 1, varpi - 1, eta + 2, delta + 1
        else:
            break
    if t2 >= 2:
        raise ValueError("T2^2 needs an additive Witt polynomial, not monomial normalization")
    family = "T2" if t2 else "eta2" if eta == 2 else "eta" if eta else "nu" if nu else "varsigma" if varsigma else "varpi" if varpi else "one"
    term = Term(family, varpi, delta, mu, two)
    return term if e2_nonzero(term) else None


def _raw_differential(term: Term, page: int) -> Term | None:
    """Formula on an already-live source; all coefficients are literal."""
    family, q, d, n, a = term.family, term.q, term.d, term.mu, term.two
    if page == 3:
        if a:
            return None
        if family == "T2":
            return Term("varsigma", 1, d - 1, n + 1)
        if family == "eta" and q % 2:
            return Term("eta2", q + 1, d - 1, n)
        if family == "varsigma" and q % 2 == 0:
            return Term("varpi", q + 2, d - 1, n + 1)
        if family == "varpi" and q % 2:
            return Term("eta", q + 1, d - 1, n)
        if family == "eta2" and q % 2:
            return Term("varsigma", q + 2, d - 2, n + 1)
    if n:
        return None
    if page == 5 and a == 0:
        if family == "one" and d % 2:
            return Term("nu", 2, d - 2)
        if family == "varpi" and q % 2 == 0 and (d - q // 2) % 2:
            return Term("nu", q + 2, d - 2)
        if family == "nu" and (d - q // 2 + q % 2) % 2:
            return Term("varpi", q + 3, d - 2, two=1)
    if page == 7:
        if family == "one" and ((d % 2 and a == 1) or (d % 4 == 2 and a == 0)):
            return Term("varsigma", 3, d - 3)
        if family == "varpi" and q % 2 == 0:
            c = d - q // 2
            if (c % 2 and a == 1) or (c % 4 == 2 and a == 0):
                return Term("varsigma", q + 3, d - 3)
    if page == 11 and family == "varsigma" and q % 2 and a == 0:
        if (d - (q - 1) // 2) % 4 == 0:
            return Term("varpi", q + 6, d - 4, two=1)
    if page == 13 and q % 2:
        residue = (d - (q - 1) // 2) % 4
        if family == "nu" and residue == 1 and a == 0:
            return Term("varpi", q + 7, d - 5)
        if family == "varpi" and residue == 3 and a == 1:
            return Term("nu", q + 6, d - 5)
    return None


def _preimage_candidates(term: Term, page: int) -> tuple[Term, ...]:
    """Reverse index formulas, never a search of the current viewport."""
    family, q, d, n, a = term.family, term.q, term.d, term.mu, term.two
    candidates = []
    if page == 3 and a == 0:
        if family == "varsigma" and n:
            if q == 1:
                candidates.append(Term("T2", d=d + 1, mu=n - 1))
            elif q >= 3:
                candidates.append(Term("eta2", q - 2, d + 2, n - 1))
        if family == "eta2" and q >= 1:
            candidates.append(Term("eta", q - 1, d + 1, n))
        if family == "varpi" and q >= 2 and n:
            candidates.append(Term("varsigma", q - 2, d + 1, n - 1))
        if family == "eta" and q >= 2:
            candidates.append(Term("varpi", q - 1, d + 1, n))
    if n:
        return tuple(candidates)
    if page == 5:
        if family == "nu" and a == 0:
            if q == 2:
                candidates.append(Term("one", d=d + 2))
            elif q >= 4:
                candidates.append(Term("varpi", q - 2, d + 2))
        if family == "varpi" and q >= 3 and a == 1:
            candidates.append(Term("nu", q - 3, d + 2))
    if page == 7 and family == "varsigma" and a == 0:
        if q == 3:
            candidates.extend(Term("one", d=d + 3, two=v) for v in (0, 1))
        elif q >= 5:
            candidates.extend(Term("varpi", q - 3, d + 3, two=v) for v in (0, 1))
    if page == 11 and family == "varpi" and q >= 7 and a == 1:
        candidates.append(Term("varsigma", q - 6, d + 4))
    if page == 13:
        if family == "varpi" and q >= 8 and a == 0:
            candidates.append(Term("nu", q - 7, d + 5))
        if family == "nu" and q >= 7 and a == 0:
            candidates.append(Term("varpi", q - 6, d + 5, two=1))
    return tuple(candidates)


@lru_cache(maxsize=200_000)
def is_live(term: Term, page: int = 2) -> bool:
    """Whether this precise coefficient representative is nonzero on E_page."""
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
    """The exact nonzero target, or None; sources are checked before mapping."""
    _page(page)
    if page not in DIFFERENTIAL_PAGES or not is_live(term, page):
        return None
    target = _raw_differential(term, page)
    if target is not None and not is_live(target, page):
        raise ArithmeticError(f"C4 formula targets an absent E{page} representative: {term} -> {target}")
    return target


def incoming(term: Term, page: int) -> tuple[Term, ...]:
    """All canonical monomial preimages for this differential page."""
    _page(page)
    if page not in DIFFERENTIAL_PAGES or not is_live(term, page):
        return ()
    return tuple(source for source in _preimage_candidates(term, page)
                 if is_live(source, page) and _raw_differential(source, page) == term)


def multiply_e2(term: Term, multiplier: str) -> Term | None:
    """Literal eta, nu, or 2 multiplication in the E2 coefficient algebra.

    This is shared with the shifted module only as an E2 algebra operation;
    its caller must take the quotient on the correct slice and page.
    """
    if multiplier not in ("eta", "nu", "2"):
        raise ValueError("C4 chart multipliers are eta, nu, and 2")
    factors = {"varpi": term.q, "delta": term.d, "mu": term.mu, "two": term.two}
    if term.family not in ("one", "varpi"):
        symbol, exponent = {"T2": ("t2", 1), "eta2": ("eta", 2)}.get(term.family, (term.family, 1))
        factors[symbol] = exponent
    factor = "two" if multiplier == "2" else multiplier
    factors[factor] = factors.get(factor, 0) + 1
    return normalize_monomial(**factors)


def multiply(term: Term, multiplier: str, page: int = 2) -> Term | None:
    """Associated-graded product, never a guessed hidden extension."""
    _page(page)
    if multiplier not in ("eta", "nu", "2"):
        raise ValueError("C4 chart multipliers are eta, nu, and 2")
    if not is_live(term, page):
        return None
    result = multiply_e2(term, multiplier)
    return result if result is not None and is_live(result, page) else None


def module_descriptor(family: str, q: int, d: int, page: int = 2) -> dict:
    """A completed coefficient ideal/quotient; no fictitious finite F4 rank."""
    _page(page)
    base = Term(family, q, d)
    branches = []
    for mu in (0, 1):
        valuations = [a for a in range(5) if is_live(Term(family, q, d, mu, a), page)]
        if not valuations:
            continue
        unbounded = family in ("one", "T2") and 4 in valuations
        lower, upper = min(valuations), None if unbounded else max(valuations)
        branches.append({
            "mu_min": mu, "mu_max": 0 if mu == 0 else None,
            "two_min": lower, "two_max": upper,
            "completed_mu_tail": mu == 1,
            "representative": asdict(Term(family, q, d, mu, lower)),
            "representative_tex": Term(family, q, d, mu, lower).tex(),
            "coefficient_description": "W(k)" if upper is None else f"2^{lower}W(k)/2^{upper+1}",
        })
    return {
        "family": family, "q": q, "d": d, "page": page,
        "stem": base.stem, "filtration": base.filtration, "label": base.tex(),
        "branches": branches, "nonzero": bool(branches),
        "base_ring": "W(k)[[mu]]", "scalar_ports_are_not_module_basis": True,
        "scope": "integer C4/C4 associated-graded HFPSS; no hidden extensions",
        "source_ref": SOURCE,
    }


def differential_components(family: str, q: int, d: int, page: int) -> list[dict]:
    """Constant and completed-tail map components, with their exact kernels.

    The positive-mu component means all mu exponents >=1, not merely its
    displayed mu^1 sample. Every nonzero component reduces Witt coefficients
    modulo 2; higher doubles are in its kernel.
    """
    result = []
    for branch in module_descriptor(family, q, d, page)["branches"]:
        source = Term(**branch["representative"])
        target = differential(source, page)
        if target is None:
            continue
        result.append({"page": page, "source": asdict(source), "target": asdict(target),
                       "source_tex": source.tex(), "target_tex": target.tex(),
                       "source_branch": branch,
                       "mu_exponent_shift": target.mu - source.mu,
                       "coefficient_map": "W(k)-linear, reduction modulo 2 of the displayed source generator",
                       "kernel_two_min": source.two + 1,
                       "source_ref": SOURCE})
    return result


def cells_in_window(*, page: int, stem_min: int, stem_max: int,
                    filtration_min: int = 0, filtration_max: int = 20) -> Iterator[dict]:
    """Clip AFTER exact page computation; liveness never depends on this box."""
    _page(page)
    for name, value in (("stem_min", stem_min), ("stem_max", stem_max),
                        ("filtration_min", filtration_min), ("filtration_max", filtration_max)):
        _integer(value, name)
    if stem_min > stem_max or filtration_min < 0 or filtration_min > filtration_max:
        raise ValueError("Invalid C4 chart window")
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


def reduce_ro_degree(alpha: int, beta: int, gamma: int) -> dict:
    """An exact permanent-unit certificate for alpha+beta*sigma+gamma*lambda.

    A *-V request must supply coefficients of -V. The returned representative
    is stem_shift + sector*(1-sigma), with stem_shift in [0,31].
    """
    for name, value in (("alpha", alpha), ("beta", beta), ("gamma", gamma)):
        _integer(value, name)
    sector = (beta - gamma) % 2
    n = alpha - 7 * beta + 6 * gamma - 8 * sector
    h = (beta - gamma + sector) // 2
    residue = n % 32
    return {
        "input": [alpha, beta, gamma], "basis": ["1", "sigma", "lambda"],
        "sector": sector, "sector_label": "1-sigma" if sector else "integer",
        "stem_shift": residue,
        "representative": [residue + sector, -sector, 0],
        "permanent_unit_powers": [
            {"unit": r"\bar d_1", "degree": [1, 1, 1], "exponent": gamma + 4 * h},
            {"unit": r"u_{2\sigma}u_\lambda^4", "degree": [10, -2, -4], "exponent": h},
            {"unit": r"\Delta_1^4", "degree": [32, 0, 0], "exponent": (n - residue) // 32},
        ],
        "source_ref": "BBHS20, Props. 4.4-4.7, 5.25; Remark 4.9",
    }
