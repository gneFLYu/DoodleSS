"""Typed previews for the cyclic action and the semilinear Galois symmetry."""
from __future__ import annotations

from .grading import normalize_to_q8_sector
from .models import C3Action, Project


def ensure_c3_action(project: Project) -> Project:
    if not any(item.id == "q8-c3-omega" for item in project.c3_actions):
        project.c3_actions.append(C3Action())
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
            "obligations": normalized.obligations,
            "display_label": representation_label(raw),
        })
    psi_image = apply_psi_representation(sector.normal_form)
    psi_normalized = normalize_to_q8_sector(project, psi_image)
    periodic_transport = None
    if sector_id == "q8-ro-a1-b1":
        periodic_transport = {
            "source_workspace_id": "ws_sigma_i",
            "source_representation": "-sigma_k = -omega^2(sigma_i)",
            "stem_shift": 16,
            "relation": "(1+sigma_i+sigma_j+sigma_k+H) - (20+H)",
            "status": "user-confirmed-source-transport",
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
            "scope_warning": "psi is semilinear: transported coefficients must be conjugated, not copied unchanged.",
        },
        "periodic_transport": periodic_transport,
        "materialization_allowed": (
            action.status in {"reviewed", "established"}
            and action.coefficient_automorphism != "identity-until-source-certified"
        ),
        "warning": "omega gives the cyclic i-j-k orbit; psi separately fixes i and swaps j,k while conjugating F4 coefficients.",
    }
