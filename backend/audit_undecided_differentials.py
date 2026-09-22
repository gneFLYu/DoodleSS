"""Print the read-only unresolved-differential audit as JSON."""
from __future__ import annotations

import json

from domain.undecided_differential_audit import audit_undecided_differentials


if __name__ == "__main__":
    print(json.dumps(audit_undecided_differentials(), indent=2, ensure_ascii=False))
