"""Source-scoped migration and validation for differential period families."""
from __future__ import annotations

from .models import Grade, PeriodFamily, PeriodGenerator, Project, Proposition


LEGACY_DIFFERENTIAL_PERIODS = {
    "diff_two_d3_u": (8, 0),
    "diff_two_d5_h2D": (16, 0),
    "diff_two_d5_2D": (16, 0),
    "diff_two_d5_xh1": (8, 0),
    "diff_two_d9": (32, 0),
    "diff_two_d11": (32, 0),
    "diff_two_d13": (32, 0),
}


def fill_legacy_period_pairs(project: Project) -> None:
    for workspace in project.workspaces:
        for differential in workspace.differentials:
            period = LEGACY_DIFFERENTIAL_PERIODS.get(differential.id)
            if period and not differential.period_stem and not differential.period_filtration:
                differential.period_stem, differential.period_filtration = period


def migrate_legacy_period_families(project: Project) -> Project:
    """Wrap raw period pairs in provisional families with explicit evidence.

    A raw pair does not prove a period.  The generated family and certificate
    therefore remain ``under-review`` and do not invent a multiplier.
    """
    fill_legacy_period_pairs(project)
    families = {item.id: item for item in project.period_families}

    for workspace in project.workspaces:
        propositions = {item.id: item for item in workspace.propositions}
        for differential in workspace.differentials:
            if not (differential.period_stem or differential.period_filtration):
                differential.unperiodic_reason = differential.unperiodic_reason or "No periodicity asserted in imported data."
                continue

            family_id = differential.period_family_id or f"period_{differential.id}"
            certificate_id = f"prop_period_{differential.id}"
            source_prop = propositions.get(differential.proposition_id)
            source_refs = list(source_prop.source_refs) if source_prop else []
            if source_prop and source_prop.source_ref and source_prop.source_ref not in source_refs:
                source_refs.append(source_prop.source_ref)
            if not source_refs:
                source_refs = ["Legacy differential period fields in project.json"]

            if certificate_id not in propositions:
                certificate = Proposition(
                    id=certificate_id,
                    kind="period-certificate",
                    statement=(
                        f"The imported period annotation for {differential.id} has shift "
                        f"({differential.period_stem}, {differential.period_filtration}); "
                        "its multiplier and permanent-cycle proof require review."
                    ),
                    status="under-review",
                    conclusion={
                        "period_family_id": family_id,
                        "anchor_differential_id": differential.id,
                    },
                    premise_ids=[differential.proposition_id] if differential.proposition_id else [],
                    rule="LegacyPeriodMigration",
                    confidence=0.5,
                    notes="The numeric pair is preserved, not promoted to a certified period.",
                    source_ref=source_refs[0],
                    source_refs=source_refs,
                    hypotheses=["A multiplier realizing this shift must be supplied."],
                    verification_checks=["permanent-cycle", "page-range", "translation"],
                )
                workspace.propositions.append(certificate)
                propositions[certificate_id] = certificate

            if family_id not in families:
                family = PeriodFamily(
                    id=family_id,
                    name=f"Imported period for {differential.id}",
                    workspace_id=workspace.id,
                    rank=1,
                    generators=[
                        PeriodGenerator(
                            grade_shift=Grade(
                                stem=differential.period_stem,
                                filtration=differential.period_filtration,
                            ),
                            multiplier_expr="unspecified legacy multiplier",
                        )
                    ],
                    valid_from_page=differential.page,
                    certificate_proposition_id=certificate_id,
                    supporting_proposition_ids=[differential.proposition_id] if differential.proposition_id else [],
                    status="under-review",
                    source_ref=source_refs[0],
                )
                project.period_families.append(family)
                families[family_id] = family

            differential.period_family_id = family_id
            differential.anchor_differential_id = differential.anchor_differential_id or differential.id
            differential.period_translation = differential.period_translation or [0]
            differential.period_notes = differential.period_notes or "Migrated from raw period_stem/period_filtration fields; certificate remains under review."

    return project


def validate_period_family(project: Project, differential) -> list[str]:
    errors: list[str] = []
    if not differential.period_family_id:
        return errors
    family = next((item for item in project.period_families if item.id == differential.period_family_id), None)
    if not family:
        return ["Unknown period family."]
    if not family.certificate_proposition_id:
        errors.append("The period family has no certificate proposition.")
    if not differential.anchor_differential_id:
        errors.append("The periodic claim has no anchor differential.")
    if len(differential.period_translation) != family.rank:
        errors.append("The period translation does not have the family rank.")
    return errors
