"""Audit a legacy DoodleSS JSON file, or explicitly install cited E2 records.

Examples (PowerShell):

    python backend/audit_e2_import.py --workspace sigma_i \
      --legacy-json ..\\frontEnd_lty\\spectral_sequence_project_newd9d11.json

    python backend/audit_e2_import.py --workspace integer --apply-verified \
      --project backend\\data\\project.json

The first command is read-only.  The second does *not* import dots from the
legacy JSON; it adds only the finite DKLLW24 catalogue in domain.e2_import.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from domain.e2_import import WORKSPACE_IDS, materialize_verified_e2_records_for_project, review_legacy_e2_payload
from domain.fate import sync_project_fates
from domain.migrations import migrate_project
from domain.models import project_from_dict, project_to_dict


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", choices=sorted(WORKSPACE_IDS), required=True)
    parser.add_argument("--legacy-json", type=Path, help="Legacy DoodleSS JSON to audit; never imported automatically.")
    parser.add_argument("--project", type=Path, help="HFPSS Studio project JSON; required with --apply-verified.")
    parser.add_argument(
        "--apply-verified",
        action="store_true",
        help="Write only the cited finite DKLLW24 catalogue and relation propositions to --project.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.legacy_json and not args.apply_verified:
        raise SystemExit("Provide --legacy-json to audit, --apply-verified to write cited records, or both.")
    if args.apply_verified and not args.project:
        raise SystemExit("--apply-verified requires --project.")

    report: dict[str, object] = {"workspace": args.workspace}
    if args.legacy_json:
        payload = json.loads(args.legacy_json.read_text(encoding="utf-8"))
        report["legacy_audit"] = review_legacy_e2_payload(payload, args.workspace).to_dict()

    if args.apply_verified:
        raw_project = json.loads(args.project.read_text(encoding="utf-8"))
        project = migrate_project(project_from_dict(raw_project))
        report["materialized"] = materialize_verified_e2_records_for_project(project, args.workspace)
        sync_project_fates(project)
        args.project.write_text(json.dumps(project_to_dict(project), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report["written_project"] = str(args.project)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
