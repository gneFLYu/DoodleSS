"""Deterministic custom-TikZ and article TeX exports for HFPSS Studio.

This module deliberately uses only ordinary TikZ.  It does not depend on the
``spectralsequences`` package: its output is a small, auditable dialect that
matches the project's custom chart vocabulary and embeds stable provenance
comments for a future restricted importer.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .fate import class_is_live_on_page, is_accepted
from .models import Differential, Project, Proposition, Workspace


TEMPLATE_SOURCE = Path(r"E:\课程\PACE2025_fly\HFPSS Q_8\Notes\Charts\2Sigma_corrected_E11above.tex")


def _template_fingerprint() -> str:
    """Identify the exact local custom-TikZ source used for the dialect."""
    if not TEMPLATE_SOURCE.is_file():
        return "unavailable"
    return hashlib.sha256(TEMPLATE_SOURCE.read_bytes()).hexdigest()


def _template_dialect() -> tuple[list[str], str]:
    """Extract the actual chart preamble and TikZ dialect from the source.

    This deliberately consumes the supplied custom template at export time:
    its colour declarations and complete style vocabulary remain the single
    source of truth, while this renderer supplies only the data layer.
    """
    if not TEMPLATE_SOURCE.is_file():
        raise FileNotFoundError(f"Custom TikZ template is unavailable: {TEMPLATE_SOURCE}")
    source = TEMPLATE_SOURCE.read_text(encoding="utf-8")
    colors = re.findall(r"^\\definecolor\{[^\n]+$", source, flags=re.M)
    match = re.search(
        r"\\begin\{tikzpicture\}\s*\n\s*\[(.*?)\]\s*\n\s*% Draw grid and axes",
        source,
        flags=re.S,
    )
    if not colors or not match:
        raise ValueError("The custom TikZ template does not contain its expected first-chart dialect.")
    return colors, match.group(1).strip()


def _node_name(identifier: str) -> str:
    """Return a stable TikZ-safe node name without changing record identity."""
    return "class_" + re.sub(r"[^A-Za-z0-9_]+", "_", identifier).strip("_")


def _tex_text(value: str) -> str:
    """Escape prose for portable pdfLaTeX output.

    Imported notes contain legacy mojibake.  The export never treats that as
    mathematical syntax; non-ASCII prose is replaced with ``?`` rather than
    making an otherwise reviewable snapshot fail to compile.
    """
    portable = value.encode("ascii", "replace").decode("ascii")
    return (portable.replace("\\", r"\textbackslash{}")
                 .replace("&", r"\&")
                 .replace("%", r"\%")
                 .replace("#", r"\#")
                 .replace("_", r"\_")
                 .replace("{", r"\{")
                 .replace("}", r"\}")
                 .replace("$", r"\$")
                 .replace("^", r"\char94{}")
                 .replace("~", r"\char126{}"))


def _proposition_for(workspace: Workspace, differential: Differential) -> Proposition | None:
    return next((item for item in workspace.propositions if item.id == differential.proposition_id), None)


def _differential_style(workspace: Workspace, differential: Differential) -> str:
    """Use the named d_r styles from the supplied 2-sigma TikZ template."""
    base = f"d{differential.page}" if differential.page in {1, 2, 3, 4, 5, 6, 7, 9, 11, 13, 17, 21, 23} else "unclassified differential"
    proposition = _proposition_for(workspace, differential)
    accepted = is_accepted(differential.status) and proposition is not None and is_accepted(proposition.status)
    return base if accepted else f"{base},review differential"


def _provenance(record: str, **fields: object) -> str:
    """Stable comments let a future restricted importer recover every record."""
    fields["record"] = record
    return "% HFPSS-STUDIO " + json.dumps(fields, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _visible_differentials(workspace: Workspace, page: int, class_ids: set[str]) -> list[Differential]:
    return [
        item for item in workspace.differentials
        if item.page == page and item.source_id in class_ids and item.target_id in class_ids
    ]


def render_chart_tex(project: Project, workspace: Workspace, page: int | None = None) -> str:
    """Render one page as a standalone custom-TikZ document.

    The export is intentionally a snapshot: accepted and under-review arrows
    are both rendered, but the latter carry a dashed amber style and an exact
    proposition/status comment instead of being made to look established.
    """
    page = int(page or workspace.page)
    nodes = [
        item for item in workspace.classes
        if not item.archived and item.page <= page and class_is_live_on_page(workspace, item.id, page)
    ]
    node_ids = {item.id for item in nodes}
    differentials = _visible_differentials(workspace, page, node_ids)
    stem_values = [item.grade.stem for item in nodes] or [0]
    filtration_values = [item.grade.filtration for item in nodes] or [0]
    min_stem, max_stem = min(stem_values) - 1, max(stem_values) + 1
    max_filtration = max(1, max(filtration_values) + 1)
    template_colors, template_options = _template_dialect()

    lines = [
        "% Generated by HFPSS Studio.  This is a source/provenance snapshot.",
        f"% workspace={workspace.id} page=E{page} revision={project.revision}",
        f"% custom_tikz_template={TEMPLATE_SOURCE.as_posix()} sha256={_template_fingerprint()}",
        r"\documentclass[tikz,border=6pt]{standalone}",
        r"\usepackage{tikz}",
        r"\usetikzlibrary{arrows.meta}",
        *template_colors,
        r"\tikzset{review differential/.style={draw={orange!90!black},dashed,opacity=.85},unclassified differential/.style={draw={orange!90!black},dashed,ultra thick}}",
        r"\begin{document}",
        rf"\begin{{tikzpicture}}[{template_options}]",
        f"  \\draw[step=1cm,black!20,very thin,xshift=0.5cm,yshift=0.5cm] ({min_stem},0) grid ({max_stem},{max_filtration});",
        f"  \\draw[->] ({min_stem},0) -- ({max_stem + 0.4},0) node[right] {{stem}};",
        f"  \\draw[->] ({min_stem},0) -- ({min_stem},{max_filtration + 0.4}) node[above] {{filtration}};",
        f"  \\node[anchor=south west] at ({min_stem + 1.2},{max_filtration + 0.25}) {{$E_{{{page}}}$: {_tex_text(workspace.name)}}};",
    ]
    fates = {item.class_id: item for item in workspace.fates}
    for node in nodes:
        fate = fates.get(node.id)
        style = "sq" if fate and fate.conclusion == "permanent_cycle" else "dot"
        name = _node_name(node.id)
        label = node.label or node.expression or node.id
        source_props = [item.id for item in workspace.propositions if item.conclusion.get("class_id") == node.id]
        lines.extend([
            "  " + _provenance("class", id=node.id, expression=node.expression or node.label,
                                grade={"stem": node.grade.stem, "filtration": node.grade.filtration, "representation": node.grade.representation},
                                coefficient_context=node.coefficient_context_id, convention=node.convention_id,
                                sector=node.sector_id, fate=(fate.conclusion if fate else "unresolved"), source_propositions=source_props),
            f"  \\node[{style}] ({name}) at ({node.grade.stem},{node.grade.filtration}) {{}};",
            f"  \\node[anchor=south west,scale=.72] at ({node.grade.stem + 0.12},{node.grade.filtration + 0.12}) {{$ {label} $}};",
        ])
    for differential in differentials:
        proposition = _proposition_for(workspace, differential)
        source = _node_name(differential.source_id)
        target = _node_name(differential.target_id)
        source_ref = proposition.source_ref if proposition else "missing proposition"
        lines.extend([
            "  " + _provenance("differential", id=differential.id, source_id=differential.source_id,
                                target_id=differential.target_id, page=differential.page, status=differential.status,
                                proposition_id=differential.proposition_id or None, source_ref=source_ref,
                                period_family_id=differential.period_family_id, period_translation=differential.period_translation,
                                anchor_differential_id=differential.anchor_differential_id),
            f"  \\draw[{_differential_style(workspace, differential)}] ({source}) -- ({target});",
        ])
    lines.extend([r"\end{tikzpicture}", r"\end{document}", ""])
    return "\n".join(lines)


def _topological_propositions(workspace: Workspace) -> list[Proposition]:
    by_id = {item.id: item for item in workspace.propositions}
    remaining = dict(by_id)
    ordered: list[Proposition] = []
    while remaining:
        ready = [
            item for item in remaining.values()
            if all(premise not in remaining for premise in item.premise_ids)
        ]
        if not ready:
            ready = [remaining[sorted(remaining)[0]]]
        for item in sorted(ready, key=lambda candidate: candidate.id):
            ordered.append(item)
            remaining.pop(item.id, None)
    return ordered


def render_article_tex(project: Project, workspace: Workspace, page: int | None = None) -> str:
    """Render a review-safe article snapshot with an embedded custom-TikZ chart."""
    page = int(page or workspace.page)
    chart = render_chart_tex(project, workspace, page)
    template_colors, template_options = _template_dialect()
    chart_body = re.sub(
        r"^.*?\\begin\{tikzpicture\}\s*\[.*?\]\s*\n(?=\s*\\draw\[step=)",
        "",
        chart,
        count=1,
        flags=re.S,
    )
    chart_body = chart_body.split(r"\end{tikzpicture}", 1)[0].strip()
    class_map = {item.id: item for item in workspace.classes}
    differentials = sorted(workspace.differentials, key=lambda item: (item.page, item.id))
    contexts = sorted({item.coefficient_context_id for item in workspace.classes if item.coefficient_context_id})
    conventions = sorted({item.convention_id for item in workspace.classes if item.convention_id})
    lines = [
        "% Generated by HFPSS Studio; review statuses are intentionally retained.",
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage{booktabs,longtable,tikz,graphicx}",
        r"\usetikzlibrary{arrows.meta}",
        f"% custom_tikz_template={TEMPLATE_SOURCE.as_posix()} sha256={_template_fingerprint()}",
        *template_colors,
        r"\tikzset{review differential/.style={draw={orange!90!black},dashed,opacity=.85},unclassified differential/.style={draw={orange!90!black},dashed,ultra thick}}",
        r"\begin{document}",
        f"\\title{{HFPSS Studio snapshot: {_tex_text(workspace.name)}}}",
        f"\\author{{RO($Q_8$)-graded HFPSS workspace { _tex_text(workspace.id) }}}",
        f"\\date{{Project revision {project.revision}; rendered page $E_{{{page}}}$}}",
        r"\maketitle",
        r"\section*{Scope and convention}",
        f"Group: {_tex_text(workspace.group)}. Theory: $ {workspace.theory} $. Grading: $ {workspace.grading_label} $. Spectral sequence: {_tex_text(workspace.spectral_sequence)}. Coefficient context(s): {_tex_text(', '.join(contexts) or 'unspecified')}. Grading convention(s): {_tex_text(', '.join(conventions) or 'unspecified')}.",
        r"\section*{Legend}",
        r"A filled circle is a class whose fate is unresolved or differential-bound; an outlined square is an accepted permanent cycle. Colored $d_r$ lines use the exact custom-template length styles. Dashed amber lines are retained review claims, not established differentials.",
        r"\section*{Chart}",
        r"\begin{center}", r"\resizebox{\textwidth}{!}{%", rf"\begin{{tikzpicture}}[{template_options}]", chart_body, r"\end{tikzpicture}%", r"}", r"\end{center}",
        r"\section*{Differential register}",
        r"\begin{longtable}{p{.06\linewidth}p{.17\linewidth}p{.17\linewidth}p{.12\linewidth}p{.14\linewidth}p{.28\linewidth}}",
        r"\toprule Page & Source & Target & Period shift / family & Status & Proposition / citation \\ \midrule \endhead",
    ]
    for item in differentials:
        source = class_map.get(item.source_id)
        target = class_map.get(item.target_id)
        proposition = _proposition_for(workspace, item)
        citation = proposition.source_ref if proposition and proposition.source_ref else "source locator required"
        lines.append(
            f"$d_{{{item.page}}}$ & ${source.label if source else _tex_text(item.source_id)}$ & "
            f"${target.label if target else _tex_text(item.target_id)}$ & "
            f"{_tex_text(f'({item.period_stem},{item.period_filtration})')} ; {_tex_text(item.period_family_id or 'unperiodic')} & {_tex_text(item.status)} & "
            f"{_tex_text(item.proposition_id or 'missing')} ; {_tex_text(citation)} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{longtable}", r"\section*{Period families}", r"\begin{longtable}{p{.22\linewidth}p{.16\linewidth}p{.22\linewidth}p{.32\linewidth}}", r"\toprule Name & Valid pages & Status & Certificate / shift \\ \midrule \endhead"])
    for family in project.period_families:
        if family.workspace_id != workspace.id:
            continue
        shifts = "; ".join(
            f"({generator.grade_shift.stem},{generator.grade_shift.filtration}) {generator.multiplier_expr}"
            for generator in family.generators
        ) or "no registered generator"
        lines.append(
            f"{_tex_text(family.name)} & {_tex_text(str(family.valid_from_page))}--"
            f"{_tex_text(str(family.valid_to_page))} & {_tex_text(family.status)} & "
            f"{_tex_text(family.certificate_proposition_id)}; {_tex_text(shifts)} " + r"\\"
        )
    lines.extend([r"\bottomrule", r"\end{longtable}", r"\section*{Proof appendix}", r"\begin{enumerate}"])
    for proposition in _topological_propositions(workspace):
        refs = "; ".join(proposition.source_refs or ([proposition.source_ref] if proposition.source_ref else [])) or "no source locator"
        lines.append(f"  \\item [{_tex_text(proposition.id)}] ({_tex_text(proposition.status)}) {_tex_text(proposition.statement)}. Rule: {_tex_text(proposition.rule)}. Source: {_tex_text(refs)}")
    lines.extend([r"\end{enumerate}", r"\section*{Review appendix}", r"\begin{itemize}"])
    for proposition in workspace.propositions:
        if proposition.status in {"candidate", "claimed", "under-review", "draft"}:
            lines.append(f"  \\item {_tex_text(proposition.id)} remains {_tex_text(proposition.status)}: {_tex_text(proposition.statement)}")
    lines.extend([r"\end{itemize}", r"\end{document}", ""])
    return "\n".join(lines)
