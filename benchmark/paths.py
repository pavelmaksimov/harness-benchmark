from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIGS_DIR = REPO_ROOT / "configs"
HARNESSES_DIR = REPO_ROOT / "harnesses"
RESULTS_DIR = REPO_ROOT / "results"
REPORTS_DIR = REPO_ROOT / "reports"
VENDOR_DIR = REPO_ROOT / "vendor"
VENDOR_PINS_PATH = VENDOR_DIR / "pins.json"
SCB_DIR = VENDOR_DIR / "slop-code-bench"
PROBLEMS_DIR = VENDOR_DIR / "scb-problems"
PONYTAIL_SKILL_PATH = HARNESSES_DIR / "ponytail" / "SKILL.md"
PONYTAIL_VERSION_PATH = HARNESSES_DIR / "ponytail" / "VERSION.json"

ACTIVATION_MARKER = "harness_activation.json"
ACTIVATION_PHRASE = "Activate and follow the installed Codex skill `ponytail`"

DEFAULT_PROBLEM = "file_backup"
DEFAULT_RUNS = 3
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_THINKING = "medium"
