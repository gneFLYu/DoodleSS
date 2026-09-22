"""Typed previews for the cyclic action and the semilinear Galois symmetry."""
from __future__ import annotations

import re

from .grading import normalize_to_q8_sector
from .algebra import F4Element
from .models import C3Action, Project


def ensure_c3_action(project: Project) -> Project:
    if not any(item.id == "q8-c3-omega" for item in project.c3_actions):
        project.c3_actions.append(C3Action())
    action = next(item for item in project.c3_actions if item.id == "q8-c3-omega")
    action.status = "established"
    action.coefficient_automorphism = "F4-linear; D -> zeta^2 D, x -> zeta x, y -> zeta^2 y"
    action.source_ref = "DKLLW24 Lemma 3.1; explicit normalizer action on Q8"
    return project


def apply_omega_representation(representation: dict[str, int], power: int = 1) -> dict[str, int]:
    output = dict(representation)
    for _ in range(power % 3):
        output = {
            **{key: value for key, value in output.items() if key not in {"sigma_i", "sigma_j", "sigma_k"}},
            "sigma_i": output.get("sigma_k", 0),
            "sigma_j": output.get("sigma_i", 0),
            "sigma_k": output.get("sigma_j", 0),
        }
        output = {key: value for key, value in output.items() if value}
    return output


def apply_omega_expression(expression: str, power: int = 1) -> str:
    output = expression
    for _ in range(power % 3):
        output = (
            output.replace("\\sigma_i", "@@SIGMA_I@@")
            .replace("\\sigma_j", "@@SIGMA_J@@")
            .replace("\\sigma_k", "@@SIGMA_K@@")
            .replace("@@SIGMA_I@@", "\\sigma_j")
            .replace("@@SIGMA_J@@", "\\sigma_k")
            .replace("@@SIGMA_K@@", "\\sigma_i")
        )
    return output


def c3_orbit(representation: dict[str, int]) -> list[dict[str, int]]:
    return [apply_omega_representation(representation, power) for power in range(3)]


def apply_psi_representation(representation: dict[str, int]) -> dict[str, int]:
    """Frobenius-normalizer action: sigma_i fixed and sigma_j, sigma_k swapped."""
    output = {
        **{key: value for key, value in representation.items() if key not in {"sigma_j", "sigma_k"}},
        "sigma_j": representation.get("sigma_k", 0),
        "sigma_k": representation.get("sigma_j", 0),
    }
    return {key: value for key, value in output.items() if value}


def frobenius_scalar(value: str) -> str:
    """Exact residue-field conjugation; never reduce Witt scalars modulo 2."""
    return str(F4Element.parse(value) ** 2)


def apply_s3_representation(representation: dict[str, int], power: int = 0, reflected: bool = False) -> dict[str, int]:
    """The normal form omega^power psi^reflected for the six permutations."""
    image = apply_psi_representation(representation) if reflected else representation
    return apply_omega_representation(image, power)


def transported_expression(expression: str, power: int = 0, reflected: bool = False) -> str:
    """Expand the certified action, including its unit (not a basis change)."""
    return expanded_action_basis(expression, power, reflected)["expanded_expression"]


_UNIT_ENCODING = (1, 2, 3)  # 1, zeta, zeta^2; never integer/Witt coefficients
_UNIT_EXPONENT = {1: 0, 2: 1, 3: 2}
_ACTION_WEIGHTS = {"D": 2, "x": 1, "y": 2, "j": 1,
                   "v_1": 0, "h_1": 0, "h_2": 0, "k": 0,
                   "g": 0, "c": 0, "d": 0}


def normalized_scalar_ratio(source_unit: int | None, target_unit: int | None) -> int | None:
    """Return beta/alpha for transported source=alpha*A and target=beta*B.

    These are Teichmuller units encoded in F4, not the integers 2 and 3.
    A missing certified unit stays unknown instead of becoming one.
    """
    if (type(source_unit) is not int or type(target_unit) is not int
            or source_unit not in _UNIT_EXPONENT or target_unit not in _UNIT_EXPONENT):
        return None
    return _UNIT_ENCODING[(_UNIT_EXPONENT[target_unit] - _UNIT_EXPONENT[source_unit]) % 3]


def _unit_latex(exponent: int) -> str:
    return ("", r"\zeta", r"\zeta^2")[exponent % 3]


def _power(base, exponent):
    if exponent == 0 or base == ("number", 1):
        return ("number", 1)
    return base if exponent == 1 else ("pow", base, exponent)


def _action_sigma_labels(text: str, power: int, reflected: bool) -> str:
    mapping = {name: name for name in ("i", "j", "k")}
    if reflected:
        mapping.update(j="k", k="j")
    cycle = {"i": "j", "j": "k", "k": "i"}
    for _ in range(power % 3):
        mapping = {key: cycle[value] for key, value in mapping.items()}
    return re.sub(r"\\sigma_(?:\{([ijk])\}|([ijk]))",
                  lambda m: r"\sigma_" + mapping[m[1] or m[2]], text)


def _product(factors):
    """Collect monomial powers and integers, with no coefficient-ring quotient."""
    flat = []
    for factor in factors:
        flat.extend(factor[1] if factor[0] == "product" else (factor,))
    integer, order, powers, others = 1, [], {}, []
    for factor in flat:
        if factor[0] == "number":
            integer *= factor[1]
        elif factor[0] == "atom" or (factor[0] == "pow" and factor[1][0] == "atom"):
            name, exponent = (factor[1], 1) if factor[0] == "atom" else (factor[1][1], factor[2])
            if name not in powers:
                order.append(name)
                powers[name] = 0
            powers[name] += exponent
        else:
            others.append(factor)
    if integer == 0:
        return ("number", 0)
    collected = [("atom", name) if powers[name] == 1 else ("pow", ("atom", name), powers[name])
                 for name in order if powers[name]]
    # Sums lead; Thom factors are last. In particular a Picard D shift is
    # combined with the class's D exponent rather than hidden in a wrapper.
    thom = [x for x in collected if (x[1] if x[0] == "atom" else x[1][1]).startswith("u_{")]
    units = [x for x in collected if (x[1] if x[0] == "atom" else x[1][1]).startswith(r"\zeta")]
    collected = [x for x in collected if x not in thom and x not in units]
    result = ([('number', integer)] if integer != 1 else []) + units + others + collected + thom
    return ("number", integer) if not result else result[0] if len(result) == 1 else ("product", tuple(result))


class _ActionExpressionParser:
    """Bounded explicit sums/products; unknown atoms are not declared invariant."""

    def __init__(self, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 2048:
            raise ValueError("No bounded algebra expression")
        # Preserve the TeX command boundary before stripping layout spaces.
        # In particular output '\\zeta D' must not reparse as unknown '\\zetaD'.
        text = re.sub(r"\\zeta\s+(?=[A-Za-z])", lambda _: r"(\zeta)", text)
        text = text.replace(r"{\zeta}", r"(\zeta)").replace(r"\zeta{}", r"(\zeta)")
        self.text = "".join(text.replace(r"\left", "").replace(r"\right", "")
                            .replace(r"\{", "(").replace(r"\}", ")")
                            .replace(r"\,", "").replace(r"\!", "")
                            .replace(r"\cdot", "*").split())
        self.text = re.sub(r"(?<![A-Za-z\\])zeta", r"\\zeta", self.text)
        self.index = 0

    def braced(self):
        start = self.index
        if self.text[start] != "{":
            raise ValueError("Expected braces")
        depth = 1
        self.index += 1
        while self.index < len(self.text) and depth:
            depth += (self.text[self.index] == "{") - (self.text[self.index] == "}")
            self.index += 1
        if depth:
            raise ValueError("Unclosed braces")
        return self.text[start + 1:self.index - 1]

    def expression(self):
        terms = [self.term()]
        while self.index < len(self.text) and self.text[self.index] in "+-":
            sign = self.text[self.index]
            self.index += 1
            term = self.term()
            terms.append(_product([("number", -1), term]) if sign == "-" else term)
        return terms[0] if len(terms) == 1 else ("sum", tuple(terms))

    def term(self):
        factors = []
        while self.index < len(self.text) and self.text[self.index] not in "+-),":
            if self.text[self.index] == "*":
                if not factors:
                    raise ValueError("Missing factor")
                self.index += 1
                continue
            factors.append(self.factor())
        if not factors:
            raise ValueError("Missing term")
        return _product(factors)

    def factor(self):
        char = self.text[self.index]
        if char == "(":
            self.index += 1
            result = self.expression()
            if self.index >= len(self.text) or self.text[self.index] != ")":
                raise ValueError("Unclosed sum")
            self.index += 1
        elif char.isdigit():
            match = re.match(r"\d+", self.text[self.index:])
            self.index += len(match[0])
            result = ("number", int(match[0]))
        else:
            match = re.match(r"\\[A-Za-z]+|[A-Za-z]", self.text[self.index:])
            if not match:
                raise ValueError("Unsupported expression token")
            name = match[0]
            self.index += len(name)
            if self.index < len(self.text) and self.text[self.index] == "_":
                self.index += 1
                if self.index >= len(self.text):
                    raise ValueError("Missing subscript")
                if self.text[self.index] == "{":
                    subscript = self.braced()
                else:
                    subscript = self.text[self.index]
                    self.index += 1
                name += "_" + (subscript if subscript in {"1", "2"} else "{" + subscript + "}")
            result = ("atom", name)
        if self.index < len(self.text) and self.text[self.index] == "^":
            self.index += 1
            if self.index >= len(self.text):
                raise ValueError("Missing exponent")
            if self.text[self.index] == "{":
                exponent = self.braced()
            else:
                match = re.match(r"-?\d+", self.text[self.index:])
                if not match:
                    raise ValueError("Nonintegral exponent")
                exponent = match[0]
                self.index += len(exponent)
            exponent = int(exponent)
            if abs(exponent) > 4096:
                raise ValueError("Unbounded exponent")
            result = _power(result, exponent)
        return result

    def parse(self):
        result = self.expression()
        if self.index != len(self.text):
            raise ValueError("Unsupported algebra expression")
        return result


def _format_action_expression(node):
    kind = node[0]
    if kind in {"atom", "number"}:
        return str(node[1])
    if kind == "pow":
        base = _format_action_expression(node[1])
        if node[1][0] in {"sum", "product"}:
            base = "(" + base + ")"
        return base if node[2] == 1 else base + "^{" + str(node[2]) + "}"
    if kind == "sum":
        return "+".join(_format_action_expression(item) for item in node[1]).replace("+-", "-")
    pieces = ["(" + _format_action_expression(item) + ")" if item[0] == "sum"
              else _format_action_expression(item) for item in node[1]]
    output = ""
    for piece in pieces:
        if re.search(r"\\[A-Za-z]+$", output) and piece[:1].isalpha():
            output += " "  # TeX command boundary, not the unwanted \\, spacer.
        output += piece
    return output


def expanded_action_basis(expression: str, power: int = 0, reflected: bool = False,
                          *, target_thom: str | None = None, stem_shift: int = 0) -> dict:
    """Certified expression and its extracted unit relative to a chosen basis.

    Integer factors (including 2/4 in Witt modules) remain integers. Only
    powers of the Teichmuller root are reduced modulo three. Sums are NOT
    reduced modulo two and no cohomological relations are guessed. For sums,
    the chosen displayed basis puts the first term's Teichmuller unit at one.
    Picard target Thom symbols denote the path-induced basis, not an assertion
    that an unspecified external Thom normalization has unit one.
    """
    power %= 3
    unknown = set()
    thom_count = 0

    def transform(node):
        nonlocal thom_count
        kind = node[0]
        if kind == "number":
            return 0, node
        if kind == "atom":
            name = node[1]
            if name in {r"\zeta", "zeta"}:
                return 2 if reflected else 1, ("number", 1)
            if name in _ACTION_WEIGHTS:
                return power * _ACTION_WEIGHTS[name] % 3, node
            if name.startswith("a_{") and re.fullmatch(r"a_\{\\sigma_[ijk]\}", name):
                axis = name[-2]
                polynomial = {"i": "(x+y)", "j": r"(\zeta x+\zeta^2y)",
                              "k": r"(\zeta^2x+\zeta y)"}[axis]
                return transform(_ActionExpressionParser(polynomial + "u_{\\sigma_" + axis + "}").parse())
            if name.startswith("u_{") and re.fullmatch(r"u_\{[0-9+\\sigma_ijkH-]+\}", name):
                thom_count += 1
                return 0, ("atom", target_thom or _action_sigma_labels(name, power, reflected))
            unknown.add(name)
            return 0, ("atom", _action_sigma_labels(name, power, reflected))
        if kind == "pow":
            unit, base = transform(node[1])
            return unit * node[2] % 3, _power(base, node[2])
        pieces = [transform(item) for item in node[1]]
        if kind == "product":
            return sum(unit for unit, _ in pieces) % 3, _product([item for _, item in pieces])
        unit = pieces[0][0]
        terms = [_product([("atom", _unit_latex(current - unit)), item]) if (current - unit) % 3 else item
                 for current, item in pieces]
        return unit, ("sum", tuple(terms))

    try:
        unit, normalized = transform(_ActionExpressionParser(expression).parse())
        if stem_shift:
            if stem_shift % 8 or target_thom is None or thom_count != 1:
                raise ValueError("Picard expansion requires one specified induced Thom factor")
            normalized = _product([normalized, ("pow", ("atom", "D"), stem_shift // 8)])
        label = _format_action_expression(normalized)
        expanded = _format_action_expression(_product([("atom", _unit_latex(unit)), normalized])) if unit else label
    except (ValueError, RecursionError):
        source_label = _action_sigma_labels(expression, power, reflected)
        return {"status": "unresolved", "expression": source_label, "expanded_expression": source_label,
                "unit": None, "unit_latex": None,
                "reason": "Expression is outside the certified action grammar; no scalar or invariant alias inferred."}
    return {
        "status": "exact" if not unknown else "unresolved", "expression": label,
        "expanded_expression": expanded, "unit": _UNIT_ENCODING[unit] if not unknown else None,
        "unit_latex": (_unit_latex(unit) or "1") if not unknown else None,
        "unknown_atoms": sorted(unknown), "omega_power": power, "reflected": reflected,
        "normalization": "Extract the first summand's Teichmuller unit; preserve every integer/Witt factor.",
        "thom_basis": "path-induced" if target_thom and stem_shift else "transported orientation",
        "picard_D_exponent": stem_shift // 8,
        "series_action": {"parameter": "j=v_1^4D^{-1}", "omega_unit": _UNIT_ENCODING[power],
                          "frobenius_power": int(reflected),
                          "rule": "Each j^n coefficient also receives zeta^(omega_power*n); no series layer is removed."},
    }


def representation_label(representation: dict[str, int]) -> str:
    terms = []
    for symbol in ("sigma_i", "sigma_j", "sigma_k", "H", "trivial"):
        coefficient = int(representation.get(symbol, 0))
        if not coefficient:
            continue
        terms.append(f"{coefficient:+d} {symbol}")
    return " ".join(terms) or "0"


def c3_transport_preview(project: Project, sector_id: str) -> dict:
    ensure_c3_action(project)
    sector = next((item for item in project.grading_sectors if item.id == sector_id), None)
    if not sector:
        raise ValueError("Unknown grading sector.")
    action = next(item for item in project.c3_actions if item.id == "q8-c3-omega")
    orbit = []
    for power, raw in enumerate(c3_orbit(sector.normal_form)):
        normalized = normalize_to_q8_sector(project, raw)
        orbit.append({
            "power": power,
            "raw_representation": raw,
            "result_sector_id": normalized.sector_id,
            "normalization_path": normalized.normalization_path,
            "normalization_status": normalized.status,
            "stem_shift": normalized.stem_shift,
            "obligations": normalized.obligations,
            "display_label": representation_label(raw),
        })
    psi_image = apply_psi_representation(sector.normal_form)
    psi_normalized = normalize_to_q8_sector(project, psi_image)
    periodic_transport = None
    if sector_id == "q8-ro-a1-b1":
        periodic_transport = {
            "source_workspace_id": "ws_3sigma_i",
            "source_representation": "-3sigma_k = -omega^2(3sigma_i)",
            "stem_shift": 16,
            "relation": "(1+sigma_i+sigma_j+sigma_k+H) - (20+H)",
            "status": "source-declared-Picard-transport",
        }
    return {
        "action_id": action.id,
        "action_status": action.status,
        "coefficient_automorphism": action.coefficient_automorphism,
        "source_sector_id": sector_id,
        "orbit": orbit,
        "galois": {
            "action_id": "q8-galois-psi",
            "representation_action": "sigma_i fixed; sigma_j <-> sigma_k",
            "coefficient_automorphism": "a -> a^2 (zeta <-> zeta^2)",
            "raw_representation": psi_image,
            "display_label": representation_label(psi_image),
            "result_sector_id": psi_normalized.sector_id,
            "normalization_status": psi_normalized.status,
            "stem_shift": psi_normalized.stem_shift,
            "scope_warning": "psi is semilinear: transported coefficients must be conjugated, not copied unchanged.",
        },
        "periodic_transport": periodic_transport,
        "materialization_allowed": (
            action.status in {"reviewed", "established"}
            and action.coefficient_automorphism != "identity-until-source-certified"
        ),
        "warning": "omega gives the cyclic i-j-k orbit; psi separately fixes i and swaps j,k while conjugating F4 coefficients.",
    }
