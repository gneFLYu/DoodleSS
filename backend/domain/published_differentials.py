"""Materialize the complete published DKLLW24 Q8-HFPSS differential tables.

The fact-chain records explain why the differentials hold, but a chart needs
the actual source and target occurrences.  Tables 8 and 9 of DKLLW24 give a
finite list modulo the permanent ``D^8`` period.  This module records that
list verbatim and installs it in the integer and single-sign workspaces.

No Thom transport is performed here: the E2 Thom isomorphism does not identify
later pages of the mixed RO(Q8) gradings.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from .models import ClassNode, Differential, Grade, Project, Proposition, Workspace


INTEGER_SOURCE = "DKLLW24 Table 8 (journal PDF p. 39; arXiv v3 main.tex lines 1868-1928)"
SIGMA_SOURCE = "DKLLW24 Table 9 (journal PDF p. 49; arXiv v3 main.tex lines 2406-2475)"

# The proof column, transcribed from the journal tables (not inferred from
# the spectral-sequence figures). The short-repeat column belongs to this
# application's derived metadata, not to either printed table.
# Table 8 row 3 literally prints 8nu=eta^3. Retain this as a quotation of
# its proof field only, never as an algebraic rewrite rule.
JOURNAL_PROOFS = {
    8: (
        "Proposition 4.10 (restriction)", "Corollary 4.15 (vanishing line) or Proposition 4.41 (restriction)",
        "Proposition 4.17 (8ν = η³)", "Proposition 4.17", "Proposition 4.28 (vanishing line)",
        "Corollary 4.32", "Corollary 4.32", "Corollary 4.16",
        "Proposition 4.18", "Proposition 4.38", "Proposition 4.38",
        "Corollary 4.34", "Corollary 4.34", "Proposition 4.30 (restriction)",
        "Proposition 4.30 (restriction) or Proposition 4.42 (vanishing line)", "Corollary 4.35",
        "Corollary 4.35", "Proposition 4.14 (vanishing line)", "Proposition 4.18 (transfer)",
        "Proposition 4.25 (hidden 2 extension)", "Proposition 4.25", "Proposition 4.14 (vanishing line)",
        "Corollary 4.22", "Corollary 4.22",
    ),
    9: (
        "Proposition 5.8", "Proposition 5.1 (restriction)", "Corollary 5.3 (module structure)", "Corollary 5.5 (module structure)",
        "Proposition 5.11", "Proposition 5.11", "Proposition 5.12 (module structure)", "Proposition 5.12",
        "Corollary 5.13", "Corollary 5.13", "Proposition 5.15 (hidden 2 extension)", "Proposition 5.15",
        "Proposition 5.19 (vanishing line)", "Proposition 5.19", "Proposition 5.19", "Proposition 5.19",
        "Corollary 5.10 (module structure)", "Corollary 5.10", "Proposition 5.20 (vanishing line or norm differential)", "Proposition 5.14 (vanishing line)",
        "Proposition 5.17 (module structure)", "Proposition 5.17",
    ),
}


def page_horizontal_period_stem(page: int) -> int:
    """Return the repeated-pattern period for a table row on ``E_page``.

    This is not an assertion that the multiplier is already an invertible
    permanent HFPSS class.  As fixed in ``RECORD.md``, an 8-, 16-, or
    32-period here means a repeated differential pattern.  Only the final
    D^8 shift is the permanent 64-stem period.  Successive deaths in the
    integer D-tower enlarge the row pattern, and the sigma_i module inherits
    the same schedule by the Leibniz rule.
    """

    if page <= 4:
        return 8
    if page <= 6:
        return 16
    if page == 7:
        return 32
    return 64


@dataclass(frozen=True)
class PublishedArrow:
    workspace_id: str
    source_label: str
    source_stem: int
    source_filtration: int
    target_label: str
    target_stem: int
    target_filtration: int
    page: int
    source_ref: str


def _arrow(
    workspace_id: str,
    source_label: str,
    source: tuple[int, int],
    target_label: str,
    page: int,
    source_ref: str,
) -> PublishedArrow:
    return PublishedArrow(
        workspace_id=workspace_id,
        source_label=source_label,
        source_stem=source[0],
        source_filtration=source[1],
        target_label=target_label,
        target_stem=source[0] - 1,
        target_filtration=source[1] + page,
        page=page,
        source_ref=source_ref,
    )


PUBLISHED_ARROWS: tuple[PublishedArrow, ...] = (
    # DKLLW24 Table 8: integer grading (24 anchors modulo D^8).
    _arrow("ws_integer", r"v_1^6", (12, 0), r"v_1^4h_1^3", 3, INTEGER_SOURCE),
    _arrow("ws_integer", r"D", (8, 0), r"D^{-2}gh_2", 5, INTEGER_SOURCE),
    _arrow("ws_integer", r"4D", (8, 0), r"D^{-2}gh_1^3", 7, INTEGER_SOURCE),
    _arrow("ws_integer", r"2D^2", (16, 0), r"D^{-1}gh_1^3", 7, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^4", (32, 0), r"Dgh_1^3", 7, INTEGER_SOURCE),
    _arrow("ws_integer", r"Dh_1", (9, 1), r"D^{-5}g^2c", 9, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^5h_1", (41, 1), r"D^{-1}g^2c", 9, INTEGER_SOURCE),
    _arrow("ws_integer", r"Dc", (16, 2), r"D^{-5}g^2dh_1", 9, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^5c", (48, 2), r"D^{-1}g^2dh_1", 9, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^2h_1", (17, 1), r"D^{-4}g^2c", 9, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^6h_1", (49, 1), r"g^2c", 9, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^2c", (24, 2), r"D^{-4}g^2dh_1", 9, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^6c", (56, 2), r"g^2dh_1", 9, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^2d", (30, 2), r"D^{-4}g^3h_1", 11, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^6d", (62, 2), r"g^3h_1", 11, INTEGER_SOURCE),
    _arrow("ws_integer", r"Ddh_1", (23, 3), r"D^{-5}g^3h_1^2", 11, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^5dh_1", (55, 3), r"D^{-1}g^3h_1^2", 11, INTEGER_SOURCE),
    _arrow("ws_integer", r"Dch_1", (17, 3), r"2D^{-8}g^4", 13, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^5ch_1", (49, 3), r"2D^{-4}g^4", 13, INTEGER_SOURCE),
    _arrow("ws_integer", r"2Dh_2", (11, 1), r"D^{-8}g^3d", 13, INTEGER_SOURCE),
    _arrow("ws_integer", r"2D^5h_2", (43, 1), r"D^{-4}g^3d", 13, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^{-1}h_1", (-7, 1), r"D^{-16}g^6", 23, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^2h_1^2", (18, 2), r"D^{-13}g^6h_1", 23, INTEGER_SOURCE),
    _arrow("ws_integer", r"D^5h_1^3", (43, 3), r"D^{-10}g^6h_1^2", 23, INTEGER_SOURCE),

    # DKLLW24 Table 9: (*-sigma_i) grading (22 anchors modulo D^8).
    _arrow("ws_sigma_i", r"(h_1+xv_1)u_{\sigma_i}", (1, 1), r"2kv_1^2u_{\sigma_i}", 3, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"v_1^2u_{\sigma_i}", (4, 0), r"h_1^3u_{\sigma_i}", 3, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"a_{\sigma_i}D", (7, 1), r"k(yh_2+xh_1v_1)Du_{\sigma_i}", 5, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(x^2+y^2)D^2u_{\sigma_i}", (14, 2), r"kxh_1^2D^2u_{\sigma_i}", 5, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(h_1^2+xh_1v_1)Du_{\sigma_i}", (10, 2), r"k^2(x+y)h_1^2D^2u_{\sigma_i}", 9, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(h_1^2+xh_1v_1)D^5u_{\sigma_i}", (42, 2), r"k^2(x+y)h_1^2D^6u_{\sigma_i}", 9, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(x+y)h_1Du_{\sigma_i}", (8, 2), r"k^2x^2h_1D^2u_{\sigma_i}", 9, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(x+y)h_1D^5u_{\sigma_i}", (40, 2), r"k^2x^2h_1D^6u_{\sigma_i}", 9, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"a_{\sigma_i}D^2", (15, 1), r"k^2(x^2+y^2)D^3u_{\sigma_i}", 9, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"a_{\sigma_i}D^6", (47, 1), r"k^2(x^2+y^2)D^7u_{\sigma_i}", 9, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(x^2+y^2)D^3u_{\sigma_i}", (22, 2), r"k^2x^3D^4u_{\sigma_i}", 9, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(x^2+y^2)D^7u_{\sigma_i}", (54, 2), r"k^2x^3D^8u_{\sigma_i}", 9, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"x^2h_1D^2u_{\sigma_i}", (15, 3), r"k^3(h_1^2+xh_1v_1)D^3u_{\sigma_i}", 11, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"x^2h_1D^6u_{\sigma_i}", (47, 3), r"k^3(h_1^2+xh_1v_1)D^7u_{\sigma_i}", 11, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"x^2h_1D^3u_{\sigma_i}", (23, 3), r"k^3(h_1^2+xh_1v_1)D^4u_{\sigma_i}", 11, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"x^2h_1D^7u_{\sigma_i}", (55, 3), r"k^3(h_1^2+xh_1v_1)D^8u_{\sigma_i}", 11, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"x^3D^4u_{\sigma_i}", (29, 3), r"k^3xh_1D^5u_{\sigma_i}", 11, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"x^3D^8u_{\sigma_i}", (61, 3), r"k^3xh_1D^9u_{\sigma_i}", 11, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"a_{\sigma_i}D^4", (31, 1), r"k^3(h_1^2+xh_1v_1)D^5u_{\sigma_i}", 13, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(h_1^2+xh_1v_1)u_{\sigma_i}", (2, 2), r"k^4(x+y)h_1^2D^2u_{\sigma_i}", 17, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(x+y)h_1^2D^2u_{\sigma_i}", (17, 3), r"k^6(x+y)h_1D^5u_{\sigma_i}", 23, SIGMA_SOURCE),
    _arrow("ws_sigma_i", r"(x+y)h_1D^7u_{\sigma_i}", (56, 2), r"k^6(x+y)D^{10}u_{\sigma_i}", 23, SIGMA_SOURCE),
)


def _normalise_label(value: str) -> str:
    value = value.split("=")[0]
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"\^\{(-?\d+)\}", r"^\1", value)
    value = value.replace(r"\left", "").replace(r"\right", "")
    value = value.replace(r"\{", "(").replace(r"\}", ")")
    return value


def _published_e2_pattern(workspace: Workspace, label: str, filtration: int) -> str:
    """Identify the E2 chart column represented by a published occurrence.

    Published tables use the convenient names ``c``, ``d`` and ``g`` while
    the finite E2 catalogue uses the underlying Table 3/6 columns.  Retaining
    the column identity lets a differential kill the matching virtual
    ``D^8``/``kD^3`` occurrence without deleting the other columns in the same
    bidegree.
    """

    value = _normalise_label(label)
    residue = filtration % 4
    # v1^(4l+2) h1^n is a j^l multiple of the v1^2 h1^n motif.
    # In particular h1 v1^6 is NOT an h1-only generator of I11/S11;
    # multiplication order in a source label must not change its column.
    v_power = re.search(r"v_1\^(-?\d+)", value)
    bo_h1 = bool(v_power and int(v_power[1]) % 4 == 2 and "h_1" in value)
    if workspace.id == "ws_integer" or workspace.settings.get("rendering", {}).get("enumerated_e2_pattern") == "integer":
        if residue == 0:
            return "I40" if "v_1" in value else "I00"
        if residue == 1:
            if bo_h1:
                return "I51"
            return "I31" if "h_2" in value else "I11"
        if residue == 2:
            if bo_h1:
                return "I62V"
            if "h_2^2" in value:
                return "I62Y"
            if "y^2" in value:
                return "I62Y"
            if "h_1^2" in value:
                return "I22H"
            if "d" in value or "x^2" in value:
                return "I62X"
            return "I02"
        if "x^2h_2" in value or "dh_2" in value:
            return "I13X"
        if bo_h1:
            return "I73V"
        if "xh_1^2" in value or "ch_1" in value or "h_2^3" in value:
            return "I13"
        if "x^2h_1" in value or "dh_1" in value:
            return "I73"
        return "I33"

    if residue == 0:
        return "S40" if "v_1^2" in value else "S00"
    if residue == 1:
        if bo_h1:
            return "S51"
        if "x+y" in value or re.search(r"(?:^|[0-9)])a_\{", value):
            return "S71"
        return "S11"
    if residue == 2:
        if bo_h1:
            return "S62V"
        if "x^2+y^2" in value:
            return "S62"
        if "yh_2" in value:
            return "S22Y"
        if "h_1^2+xh_1v_1" in value or ("h_1+xv_1" in value and value.count("h_1") > 1):
            return "S22H"
        return "S02"
    if bo_h1:
        return "S73V"
    if "x^2h_1" in value:
        return "S73"
    if "x^3" in value:
        return "S53"
    if "x+y" in value or "xh_1^2" in value:
        return "S13"
    return "S33"


def endpoint_component_style(label: str) -> dict:
    """Record coefficient/submodule ports independently of a whole cell.

    In particular v1^4 h1^3 is j times h1^3 D, not the constant term.
    Leading 2 and 4 are 2-adic levels, not new independent cell generators.
    """
    value = _normalise_label(label)
    coefficient = re.match(r"^(\d+)", value)
    number = int(coefficient[1]) if coefficient else 1
    valuation = 0
    while number and number % 2 == 0:
        valuation += 1
        number //= 2
    v_power = re.search(r"v_1\^(-?\d+)", value)
    exponent = int(v_power[1]) if v_power else 0
    # v1^6 is the primitive filtration-zero odd bo family; its h1 products
    # are j times the primitive v1^2 h1^n families.
    j_order = exponent // 4 if "h_1" in value else 0
    return {"two_valuation": valuation, "j_order": j_order}


def _node_for(workspace: Workspace, label: str, stem: int, filtration: int, ordinal: int) -> ClassNode:
    wanted = _normalise_label(label)
    managed_id = f"published_class_{workspace.id}_{ordinal}"
    def retired_source_alias(item: ClassNode) -> bool:
        # Schema retirement is not a page death or a user's archive action.
        # Such aliases remain for provenance, but must not capture new maps.
        return item.archived and "source-schema correction" in item.archived_reason

    # One square is one Witt-vector/2-adic tower visually, but its coefficient
    # levels remain distinct spectral-sequence occurrences.  Table 8's D, 4D,
    # and 2D^2 therefore share glyph placement without sharing a class id or
    # fate.  Collapsing them is what previously removed two entire d7 families.
    scalar_level = bool(re.match(r"^[24](?!\^)", wanted)) and filtration % 4 == 0
    if scalar_level:
        same_cell_witt = next((
            item for item in workspace.classes
            if item.grade.stem == stem
            and item.grade.filtration == filtration
            and not retired_source_alias(item)
            and not item.style.get("coefficient_port")
            and (
                item.style.get("dkllw_glyph") == "witt-j-series"
                or item.style.get("module_pattern") == "witt-j-series"
            )
        ), None)
        port_style = {
            **endpoint_component_style(label),
            "published_differential_occurrence": True,
            "coefficient_port": True,
            "coefficient_parent_id": same_cell_witt.id if same_cell_witt else "",
            "e2_pattern": _published_e2_pattern(workspace, label, filtration),
            "dkllw_glyph": "witt-j-series",
            "witt_scalar_level": label,
        }
        node = next((item for item in workspace.classes if item.id == managed_id), None)
        if node is None:
            node = ClassNode(
                id=managed_id,
                label=label,
                expression=label,
                grade=Grade(stem, filtration, {} if workspace.id == "ws_integer" else {"sigma_i": -1}),
                page=2,
                notes=(
                    "Coefficient port for one row of the complete DKLLW24 differential table. "
                    "It shares a Witt-square glyph with its parent cell but has an independent fate."
                ),
                style=port_style,
                period_stem=64,
            )
            workspace.classes.append(node)
        else:
            node.label = label
            node.expression = label
            node.grade = Grade(stem, filtration, {} if workspace.id == "ws_integer" else {"sigma_i": -1})
            node.notes = (
                "Coefficient port for one row of the complete DKLLW24 differential table. "
                "It shares a Witt-square glyph with its parent cell but has an independent fate."
            )
            node.style.update(port_style)
            node.period_stem = 64
            if node.archived_reason.startswith((
                "Scalar level of the same DKLLW Witt-vector square",
                "Superseded by the complete DKLLW24",
            )):
                node.archived = False
                node.archived_reason = ""
        return node
    node = next((
        item for item in workspace.classes
        if item.grade.stem == stem
        and item.grade.filtration == filtration
        and not retired_source_alias(item)
        and _normalise_label(item.label) == wanted
    ), None)
    if node is not None:
        node.style.update(endpoint_component_style(label))
        node.style["e2_pattern"] = _published_e2_pattern(workspace, label, filtration)
        if node.archived_reason == "Superseded by the complete DKLLW24 published-table import.":
            node.archived = False
            node.archived_reason = ""
        return node
    node = next((item for item in workspace.classes if item.id == managed_id), None)
    if node is not None:
        # Migrations may correct a published label or coordinate, but a local
        # archive/clear action is lifecycle state and must survive the read.
        node.label = label
        node.expression = label
        node.grade = Grade(stem, filtration, {} if workspace.id == "ws_integer" else {"sigma_i": -1})
        node.notes = "Explicit source or target occurrence in the complete published DKLLW24 differential table."
        node.style.update({
            **endpoint_component_style(label),
            "published_differential_occurrence": True,
            "e2_pattern": _published_e2_pattern(workspace, label, filtration),
            "dkllw_glyph": "dot",
        })
        node.period_stem = 64
        return node
    node = ClassNode(
        id=managed_id,
        label=label,
        expression=label,
        grade=Grade(stem, filtration, {} if workspace.id == "ws_integer" else {"sigma_i": -1}),
        page=2,
        notes="Explicit source or target occurrence in the complete published DKLLW24 differential table.",
        style={
            **endpoint_component_style(label),
            "published_differential_occurrence": True,
            "e2_pattern": _published_e2_pattern(workspace, label, filtration),
            "dkllw_glyph": "dot",
        },
        period_stem=64,
    )
    workspace.classes.append(node)
    return node


def ensure_published_differential_charts(project: Project) -> Project:
    """Install Tables 8 and 9 and record their exact page convergence."""

    if project.id != "hfpss_studio":
        return project
    workspaces = {item.id: item for item in project.workspaces}
    for workspace_id in ("ws_integer", "ws_sigma_i"):
        workspace = workspaces.get(workspace_id)
        if workspace is None:
            continue
        managed = {
            item.id for item in workspace.differentials
            if item.id.startswith(("published_diff_", "leibniz_diff_"))
            or item.id in {"diff_int_d5_D", "diff_int_d5_D2"}
        }
        workspace.differentials = [item for item in workspace.differentials if item.id not in managed]
        workspace.differential_events = [
            item for item in workspace.differential_events
            if item.differential_claim_id not in managed
            and not item.differential_claim_id.startswith("published_diff_")
        ]
        workspace.propositions = [
            item for item in workspace.propositions
            if not item.id.startswith(("published_prop_", "leibniz_prop_"))
        ]
        workspace.settings["known_page_max"] = 24
        workspace.settings["convergence"] = {
            "last_nonzero_differential": 23,
            "stable_from_page": 24,
            "status": "published-complete",
            "source_ref": INTEGER_SOURCE if workspace_id == "ws_integer" else SIGMA_SOURCE,
        }
        workspace.settings["published_page_schedule"] = (
            [3, 5, 7, 9, 11, 13, 23]
            if workspace_id == "ws_integer"
            else [3, 5, 9, 11, 13, 17, 23]
        )

        # Supersede the demo endpoints with the coefficient-sensitive table
        # and Leibniz records. d5(D^2)=2D^-1 g h2 is nonzero (prop:d7one).
        obsolete_seed_nodes = {
            "ws_integer": {
                "int_D2": ("D^2", 16, 0), "int_h2D2": ("2kh_2D^2", 15, 5),
                "int_h2D": ("kh_2D", 7, 5), "int_Dinvh1": ("D^{-1}h_1", -8, 1),
            },
            "ws_sigma_i": {"sig_x3": (r"x^3D^4u_{\sigma_i}", 32, 3)},
        }[workspace_id]
        for node in workspace.classes:
            original_representation = {} if workspace_id == "ws_integer" else {"sigma_i": -1}
            snapshot = (node.label, node.grade.stem, node.grade.filtration)
            if (workspace_id == "ws_integer" and node.id == "int_D8"
                    and snapshot == ("D^8", 64, 0) and node.grade.representation == {}):
                node.style.update({"e2_pattern": "I00", "two_valuation": 0, "j_order": 0})
            if (obsolete_seed_nodes.get(node.id) == snapshot
                    and node.grade.representation == original_representation and not node.archived):
                node.archived = True
                node.archived_reason = "Superseded by the complete DKLLW24 published-table import."
        if workspace_id == "ws_integer":
            # The old interactive demo stored the d3 family twice from a
            # misnamed v1^4 D^-1 point.  Table 8 identifies the source as the
            # D-periodic v1^6 family, so retain the published anchor only.
            bad_demo_sources = {
                node.id for node in workspace.classes
                if node.id.startswith("e2_integer_")
                and _normalise_label(node.label) == _normalise_label(r"v_1^4D^{-1}")
                and (node.grade.stem, node.grade.filtration) == (4, 0)
            }
            # Archive only the generated obsolete glyph. User claims and
            # arrows attached to it remain recoverable research evidence.
            for node in workspace.classes:
                if node.id in bad_demo_sources and not node.archived:
                    node.archived = True
                    node.archived_reason = (
                        "Incorrect demo d3 source; replaced by the D-periodic v_1^6 family from DKLLW24 Table 8."
                    )

    ordinals: dict[str, int] = {"ws_integer": 0, "ws_sigma_i": 0}
    for index, arrow in enumerate(PUBLISHED_ARROWS, start=1):
        workspace = workspaces.get(arrow.workspace_id)
        if workspace is None:
            continue
        ordinals[arrow.workspace_id] += 1
        table_number = 8 if arrow.workspace_id == "ws_integer" else 9
        table_row = ordinals[arrow.workspace_id]
        # d7(D^4) repeats by D^8: a D^4 repeat would falsely kill 1 and D^8.
        # The two 2-divisible d7 sources have a vanishing extra Leibniz term.
        pattern_period = 64 if arrow.workspace_id == "ws_integer" and table_row == 5 else page_horizontal_period_stem(arrow.page)
        pattern_multiplier = {
            8: "D",
            16: "D^2",
            32: "D^4",
            64: "D^8",
        }[pattern_period]
        source = _node_for(
            workspace, arrow.source_label, arrow.source_stem, arrow.source_filtration,
            2 * ordinals[arrow.workspace_id] - 1,
        )
        target = _node_for(
            workspace, arrow.target_label, arrow.target_stem, arrow.target_filtration,
            2 * ordinals[arrow.workspace_id],
        )
        differential_id = f"published_diff_{arrow.workspace_id}_{index}"
        proposition_id = f"published_prop_{arrow.workspace_id}_{index}"
        workspace.propositions.append(Proposition(
            id=proposition_id,
            kind="differential",
            statement=rf"d_{{{arrow.page}}}({arrow.source_label})={arrow.target_label}",
            status="established",
            conclusion={
                "source_id": source.id,
                "target_id": target.id,
                "page": arrow.page,
                "table_complete": True,
                "table_number": table_number,
                "table_row": table_row,
                "printed_proof": JOURNAL_PROOFS[table_number][table_row - 1],
                "period_stem": pattern_period,
                "period_multiplier": pattern_multiplier,
                "period_kind": "repeated-differential-pattern",
                "period_is_invertible": pattern_period == 64,
                "period_source": "Table row + integer D^m fate + Leibniz rule",
                "period_equation_scope": "exact-D8-transport" if pattern_period == 64 else "nonzero-map-pattern-up-to-unit",
                "evidence_kind": "printed-table-row",
            },
            rule="DKLLW24 published generating differential",
            confidence=1.0,
            notes=(
                f"Table {table_number}, row {table_row}. The nonzero map pattern "
                f"repeats every {pattern_period} stems ({pattern_multiplier}), up to units for short repeats. "
                "For periods below 64 this is pattern language, not invertibility; "
                "D^8 is the permanent HFPSS period."
            ),
            source_ref=f"{arrow.source_ref}; {JOURNAL_PROOFS[table_number][table_row - 1]}",
            source_refs=[arrow.source_ref, JOURNAL_PROOFS[table_number][table_row - 1]],
        ))
        workspace.differentials.append(Differential(
            id=differential_id,
            source_id=source.id,
            target_id=target.id,
            page=arrow.page,
            status="established",
            label=f"DKLLW24 Table {table_number} row {table_row} · d{arrow.page}",
            period_stem=pattern_period,
            proposition_id=proposition_id,
            period_notes=(
                f"Derived row repeat: {pattern_multiplier}, {pattern_period} stems, "
                "by integer D^m fate and Leibniz; short repeats preserve images up to units, not necessarily literal coefficients. "
                "This is a repeated differential pattern, not an invertibility claim, "
                "unless the multiplier is D^8."
            ),
        ))
    from .published_products import derived_published_arrows
    for index, derived in enumerate(derived_published_arrows(), start=1000):
        arrow = derived.arrow
        workspace = workspaces.get(arrow.workspace_id)
        if workspace is None:
            continue
        source = _node_for(workspace, arrow.source_label, arrow.source_stem, arrow.source_filtration, 2 * index)
        target = _node_for(workspace, arrow.target_label, arrow.target_stem, arrow.target_filtration, 2 * index + 1)
        for node, pattern, j_order, two in (
            (source, derived.source_pattern, derived.source_j_order, derived.source_two_valuation),
            (target, derived.target_pattern, derived.target_j_order, derived.target_two_valuation),
        ):
            node.style.update({"e2_pattern": pattern, "j_order": j_order, "two_valuation": two})
        diff_id, prop_id = f"leibniz_diff_{derived.key}", f"leibniz_prop_{derived.key}"
        workspace.propositions.append(Proposition(
            id=prop_id, kind="differential", status="established",
            statement=rf"d_{{{arrow.page}}}({arrow.source_label})={arrow.target_label}",
            conclusion={"source_id": source.id, "target_id": target.id, "page": arrow.page,
                        "origin_table": derived.origin_table, "origin_row": derived.origin_row,
                        "target_reduction": derived.target_reduction,
                        "evidence_kind": "derived-hidden-2-extension" if derived.key == "integer_d7_4D3" else "derived-product",
                        "period_stem": derived.period_stem,
                        "period_kind": "repeated-differential-pattern",
                        "period_equation_scope": "exact-D8-transport" if derived.period_stem == 64 else "nonzero-map-pattern-up-to-unit"},
            rule=derived.derivation, confidence=1.0, source_ref=arrow.source_ref,
            source_refs=[arrow.source_ref],
        ))
        workspace.differentials.append(Differential(
            id=diff_id, source_id=source.id, target_id=target.id, page=arrow.page,
            status="established", label=f"Table {derived.origin_table} row {derived.origin_row} · {'hidden 2-extension' if derived.key == 'integer_d7_4D3' else 'derived product'}: {derived.key}",
            proposition_id=prop_id, period_stem=derived.period_stem,
            period_notes=f"{derived.derivation}; repeated pattern {derived.period_stem} stems.",
        ))

    # Retire obsolete managed endpoints left by an older table schema without
    # deleting user annotations, arrows, original IDs, or historical fates.
    # Current endpoints are updated in place above so their archived state is
    # never reset merely by loading the project.
    for workspace_id in ("ws_integer", "ws_sigma_i"):
        workspace = workspaces.get(workspace_id)
        if workspace is None:
            continue
        referenced = {
            endpoint
            for item in workspace.differentials
            if item.id.startswith(("published_diff_", "leibniz_diff_"))
            for endpoint in (item.source_id, item.target_id)
        }
        stale_managed = {
            item.id for item in workspace.classes
            if item.id.startswith(f"published_class_{workspace_id}_") and item.id not in referenced
        }
        if stale_managed:
            reason = (
                "Retired generated table endpoint after source-schema correction. "
                "Original class ID and user claims are retained; this is not a spectral-sequence death."
            )
            for item in workspace.classes:
                if item.id in stale_managed and not item.archived:
                    item.archived = True
                    item.archived_reason = reason
            for item in workspace.propositions:
                references_stale = any(item.conclusion.get(field) in stale_managed
                                       for field in ("class_id", "source_id", "target_id"))
                if (references_stale and item.id.startswith("source_e2_")
                        and item.rule.startswith("DKLLW24 E2")):
                    item.status = "superseded"
                    item.conclusion["source_schema_retirement"] = reason
    return project


def published_arrow_counts() -> dict[str, int]:
    return {
        workspace_id: sum(1 for item in PUBLISHED_ARROWS if item.workspace_id == workspace_id)
        for workspace_id in ("ws_integer", "ws_sigma_i")
    }
