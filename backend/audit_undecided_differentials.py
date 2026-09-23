"""Print the read-only unresolved-differential audit as JSON."""
from __future__ import annotations

import json
import argparse
from pathlib import Path

from domain.undecided_differential_audit import audit_undecided_differentials


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--project", type=Path, help="Read an existing project JSON without migrating or changing it")
    source.add_argument("--demo", action="store_true", help="Inspect a freshly migrated in-memory demo")
    parser.add_argument("--workspace", help="Restrict the audit to an exact workspace ID")
    parser.add_argument("--json", action="store_true", help="Emit JSON (the default output format)")
    args = parser.parse_args()
    project = None
    if args.project:
        from domain.models import project_from_dict
        raw = json.loads(args.project.read_text(encoding="utf-8"))
        project = project_from_dict(raw.get("project", raw))
    elif args.demo:
        from domain.migrations import migrate_project
        from domain.seed import demo_project
        project = migrate_project(demo_project())
    print(json.dumps(audit_undecided_differentials(project=project, workspace_id=args.workspace),
                     indent=2, ensure_ascii=False))
