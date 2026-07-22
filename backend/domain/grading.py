"""The persisted 4-by-4 Q8 grading atlas and conservative normalization."""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import GradingSector, Project, RepresentationRelation, Workspace


ATLAS_CONTEXT_ID = "q8-ro-tile-source-scoped-v1"
EXISTING_WORKSPACE_BY_SECTOR = {
    (0, 0): "ws_integer",
    (1, 0): "ws_sigma_i",
    (2, 0): "ws_2sigma_i",
    (3, 0): "ws_3sigma_i",
    (1, 2): "ws_sigma_i_2sigma_j",
}


def q8_sector_id(a: int, b: int) -> str:
    return f"q8-ro-a{a}-b{b}"


def q8_sector_label(a: int, b: int) -> str:
    terms: list[str] = []
    if a:
        terms.append("\\sigma_i" if a == 1 else f"{a}\\sigma_i")
    if b:
        terms.append("\\sigma_j" if b == 1 else f"{b}\\sigma_j")
    return "(*)" if not terms else f"(* - {' - '.join(terms)})"


def q8_representatives() -> list[tuple[int, int, str, str]]:
    return [
        (a, b, q8_sector_id(a, b), q8_sector_label(a, b))
        for a in range(4)
        for b in range(4)
    ]


def _orbit_key(vector: tuple[int, int, int]) -> tuple[int, int, int]:
    rotations = (vector, (vector[2], vector[0], vector[1]), (vector[1], vector[2], vector[0]))
    return min(rotations)


def _orbit_position(vector: tuple[int, int, int]) -> int:
    canonical = _orbit_key(vector)
    current = canonical
    for power in range(3):
        if current == vector:
            return power
        current = (current[2], current[0], current[1])
    return 0


def ensure_representation_relations(project: Project) -> None:
    existing = {item.id: item for item in project.representation_relations}
    defaults = [
        RepresentationRelation(
            id="q8-rel-four-sigma-i",
            name="4 sigma_i versus the integer shift",
            relation_vector={"sigma_i": 4, "trivial": -4},
            status="under-review",
            source_refs=["Notes/charts.tex periodic-relation matrix"],
            notes="Stored as a source-scoped normalization obligation, not a universal equality.",
        ),
        RepresentationRelation(
            id="q8-rel-four-sigma-j",
            name="4 sigma_j versus the integer shift",
            relation_vector={"sigma_j": 4, "trivial": -4},
            status="under-review",
            source_refs=["Notes/charts.tex periodic-relation matrix"],
            notes="Stored as a source-scoped normalization obligation, not a universal equality.",
        ),
        RepresentationRelation(
            id="q8-rel-norm-h",
            name="Norm/H relation",
            relation_vector={"trivial": 1, "sigma_i": 1, "sigma_j": 1, "sigma_k": 1, "H": 1},
            status="under-review",
            source_refs=["Notes/Note/record/note.tex; DKLLW Corollary 2.22"],
        ),
        RepresentationRelation(
            id="q8-rel-twenty-h",
            name="20 + H Tate-derived period",
            relation_vector={"trivial": 20, "H": 1},
            status="under-review",
            source_refs=["Notes/Note/record/note.tex, 20+H discussion"],
        ),
        RepresentationRelation(
            id="q8-rel-d8-integer",
            name="D^8 integer period",
            relation_vector={"trivial": 64},
            status="under-review",
            source_refs=["Notes/charts.tex; cited integer convention"],
        ),
    ]
    for relation in defaults:
        existing.setdefault(relation.id, relation)
    project.representation_relations = list(existing.values())


def ensure_q8_atlas(project: Project) -> Project:
    """Persist every sector and its workspace, including empty calculations."""
    ensure_representation_relations(project)
    workspaces = {item.id: item for item in project.workspaces}
    old_sectors = {item.id: item for item in project.grading_sectors}
    sectors: list[GradingSector] = []

    for a, b, sector_id, label in q8_representatives():
        workspace_id = EXISTING_WORKSPACE_BY_SECTOR.get((a, b), f"ws_{sector_id}")
        workspace = workspaces.get(workspace_id)
        if workspace is None:
            workspace = Workspace(
                id=workspace_id,
                name=f"Q8 HFPSS - {label}",
                grading_label=label,
                spectral_sequence="hfpss",
                summary="Atlas sector is stored but has not yet been computed; empty does not mean zero.",
            )
            project.workspaces.append(workspace)
            workspaces[workspace_id] = workspace

        vector = (-a, -b, 0)
        orbit_key = _orbit_key(vector)
        sector = old_sectors.get(sector_id) or GradingSector(
            id=sector_id,
            a=a,
            b=b,
            normal_form={"sigma_i": -a, "sigma_j": -b, "sigma_k": 0, "H": 0, "trivial": 0},
            display_label=label,
            period_reduction_context_id=ATLAS_CONTEXT_ID,
            workspace_id=workspace_id,
        )
        sector.a = a
        sector.b = b
        sector.normal_form = {"sigma_i": -a, "sigma_j": -b, "sigma_k": 0, "H": 0, "trivial": 0}
        sector.display_label = label
        sector.period_reduction_context_id = ATLAS_CONTEXT_ID
        sector.workspace_id = workspace_id
        sector.class_ids = [item.id for item in workspace.classes if not item.archived]
        sector.status = "imported" if sector.class_ids else "not-computed"
        sector.c3_orbit_id = f"q8-c3-orbit-{orbit_key[0]}-{orbit_key[1]}-{orbit_key[2]}"
        sector.c3_position = _orbit_position(vector)
        sector.symmetry_status = "distinct"
        for node in workspace.classes:
            node.sector_id = sector_id
        sectors.append(sector)

    project.grading_sectors = sectors
    project.research_brief["reduction"] = (
        "RO(Q8) finite atlas: all 16 (* - a sigma_i - b sigma_j), 0<=a,b<=3, "
        "are persisted; no quotient by i/j transposition is applied."
    )
    return project


@dataclass
class NormalizationResult:
    raw_representation: dict[str, int]
    sector_id: str | None
    normalization_path: list[str] = field(default_factory=list)
    status: str = "exact"  # exact | requires-certificate | unknown
    obligations: list[str] = field(default_factory=list)


def normalize_to_q8_sector(project: Project, representation: dict[str, int]) -> NormalizationResult:
    raw = {key: int(value) for key, value in representation.items() if int(value)}
    unsupported = {key: value for key, value in raw.items() if key not in {"sigma_i", "sigma_j"}}
    if unsupported:
        return NormalizationResult(
            raw,
            None,
            status="unknown",
            obligations=["A certified norm/20+H reduction is required for sigma_k, H, or trivial coordinates."],
        )

    a = -raw.get("sigma_i", 0)
    b = -raw.get("sigma_j", 0)
    if 0 <= a <= 3 and 0 <= b <= 3:
        return NormalizationResult(raw, q8_sector_id(a, b))

    reduced_a, reduced_b = a % 4, b % 4
    path: list[str] = []
    if reduced_a != a:
        path.append("q8-rel-four-sigma-i")
    if reduced_b != b:
        path.append("q8-rel-four-sigma-j")
    relation_status = {item.id: item.status for item in project.representation_relations}
    certified = all(relation_status.get(item) in {"reviewed", "established"} for item in path)
    return NormalizationResult(
        raw,
        q8_sector_id(reduced_a, reduced_b),
        normalization_path=path,
        status="exact" if certified else "requires-certificate",
        obligations=[] if certified else ["The required representation-period relations are still under review."],
    )
