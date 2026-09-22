"""The Q8 grading atlas with explicit Picard-period normalization."""
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
            status="established",
            source_refs=["DKLLW24 Corollary 2.23 (u_4sigma periodicity)"],
            notes="Multiplication by the invertible permanent u_4sigma_i; a Picard relation, not equality in RO(Q8).",
        ),
        RepresentationRelation(
            id="q8-rel-four-sigma-j",
            name="4 sigma_j versus the integer shift",
            relation_vector={"sigma_j": 4, "trivial": -4},
            status="established",
            source_refs=["DKLLW24 Corollary 2.23 (u_4sigma periodicity)"],
            notes="Multiplication by the invertible permanent u_4sigma_j; a Picard relation, not equality in RO(Q8).",
        ),
        RepresentationRelation(
            id="q8-rel-norm-h",
            name="Norm/H relation",
            relation_vector={"trivial": 1, "sigma_i": 1, "sigma_j": 1, "sigma_k": 1, "H": 1},
            status="established",
            source_refs=["DKLLW24 Corollary 2.22, norm of Delta_1"],
        ),
        RepresentationRelation(
            id="q8-rel-twenty-h",
            name="20 + H Tate-derived period",
            relation_vector={"trivial": 20, "H": 1},
            status="source-declared",
            source_refs=["formal_notes.tex H-page remark, lines 1016-1022"],
            notes="The exceptional period is declared in the notes; its Tate-to-HFPSS comparison is a separate source obligation.",
        ),
        RepresentationRelation(
            id="q8-rel-d8-integer",
            name="D^8 integer period",
            relation_vector={"trivial": 64},
            status="established",
            source_refs=["DKLLW24 Proposition 4.1, invertible permanent D^8"],
        ),
    ]
    for relation in defaults:
        # These are maintained source records, including the explicit distinction
        # between published periods and the notes' exceptional 20+H assertion.
        previous = existing.get(relation.id)
        if previous is None or previous.status in {"under-review", "source-declared"}:
            existing[relation.id] = relation
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
        sector.symmetry_status = "transported" if workspace.settings.get("atlas_transport") else "representative"
        for node in workspace.classes:
            node.sector_id = sector_id
        sectors.append(sector)

    project.grading_sectors = sectors
    project.research_brief["reduction"] = (
        "RO(Q8) finite atlas: all 16 (* - a sigma_i - b sigma_j), 0<=a,b<=3, "
        "are persisted. C3 and semilinear psi give explicit S3 transports, with Picard stem shifts and coefficient conjugation."
    )
    return project


@dataclass
class NormalizationResult:
    raw_representation: dict[str, int]
    sector_id: str | None
    normalization_path: list[str] = field(default_factory=list)
    status: str = "exact"  # exact | requires-certificate | unknown
    obligations: list[str] = field(default_factory=list)
    integer_shift: int = 0
    stem_shift: int = 0
    relation_multiplicities: dict[str, int] = field(default_factory=dict)


def normalize_to_q8_sector(project: Project, representation: dict[str, int]) -> NormalizationResult:
    raw = {key: int(value) for key, value in representation.items() if int(value)}
    unsupported = {key: value for key, value in raw.items() if key not in {"sigma_i", "sigma_j", "sigma_k", "H", "trivial"}}
    if unsupported:
        return NormalizationResult(
            raw,
            None,
            status="unknown",
            obligations=["Unknown representation coordinates: " + ", ".join(sorted(unsupported))],
        )

    x, y, z, h = (raw.get(key, 0) for key in ("sigma_i", "sigma_j", "sigma_k", "H"))
    # Subtract z*(1+i+j+k+H) and (h-z)*(20+H), then reduce
    # i,j using 4*sigma=4.  Retain the integer coordinate: discarding it
    # was the old source of wrong S11/S33 identifications.
    reduced_a, reduced_b = (z - x) % 4, (z - y) % 4
    qi, qj = (x - z + reduced_a) // 4, (y - z + reduced_b) // 4
    multiplicities = {key: count for key, count in {
        "q8-rel-norm-h": z,
        "q8-rel-twenty-h": h - z,
        "q8-rel-four-sigma-i": qi,
        "q8-rel-four-sigma-j": qj,
    }.items() if count}
    integer_shift = raw.get("trivial", 0) + 19 * z - 20 * h + 4 * qi + 4 * qj
    # The chart convention is s+dim(V)-V, not s-V.
    stem_shift = integer_shift - (x + y + z + 4 * h) - reduced_a - reduced_b
    path = list(multiplicities)
    relation_status = {item.id: item.status for item in project.representation_relations}
    certified = all(relation_status.get(item) in {"reviewed", "established"} for item in path)
    declared = all(relation_status.get(item) in {"reviewed", "established", "source-declared"} for item in path)
    return NormalizationResult(
        raw,
        q8_sector_id(reduced_a, reduced_b),
        normalization_path=path,
        status="exact" if certified else "source-declared" if declared else "requires-certificate",
        obligations=[] if certified else ["The exceptional 20+H period uses the formal-notes Tate-to-HFPSS comparison."],
        integer_shift=integer_shift,
        stem_shift=stem_shift,
        relation_multiplicities=multiplicities,
    )
