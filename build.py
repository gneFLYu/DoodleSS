"""Prepare static assets for Vercel's public CDN before deployment."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "backend" / "static"
DESTINATION = ROOT / "public" / "static"


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for source_file in SOURCE.iterdir():
        if source_file.is_file():
            shutil.copy2(source_file, DESTINATION / source_file.name)


if __name__ == "__main__":
    main()
