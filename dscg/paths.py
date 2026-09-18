"""Project paths that do not depend on the process working directory."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
FONT_DIR = ASSETS_DIR / "fonts"
DOCS_DIR = PROJECT_ROOT / "docs"
FIGURES_DIR = DOCS_DIR / "figures"
BENCHMARK_FIGURES_DIR = FIGURES_DIR / "benchmarks"
RESULTS_DIR = PROJECT_ROOT / "results"
BENCHMARK_RESULTS_DIR = RESULTS_DIR / "benchmarks"
DASHBOARD_RESULTS_DIR = RESULTS_DIR / "dashboard"

