"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure offline-friendly defaults
os.environ.setdefault("AEGIS_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("AEGIS_LLM_PROVIDER", "mock")
os.environ.setdefault("AEGIS_LOG_JSON", "false")
os.environ.setdefault("AEGIS_ENABLE_METRICS", "true")

# Make src importable when running pytest from the project root
ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(ROOT))
