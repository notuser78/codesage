"""Pytest configuration for repository tests."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_SERVICE_PATH = ROOT / "services" / "analysis"

if str(ANALYSIS_SERVICE_PATH) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_SERVICE_PATH))
