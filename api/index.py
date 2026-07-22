"""Vercel's WSGI entry point for HFPSS Studio.

The application itself remains in ``backend/`` so the local PowerShell
launcher and the Vercel Function execute the identical Flask app.
"""

from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app  # noqa: E402,F401 - Vercel discovers this WSGI variable.
