import os
from pathlib import Path


def find_project_root() -> Path:
    # Walk up to find pyproject.toml or .git
    curr = Path.cwd()
    for parent in [curr] + list(curr.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return curr


PROJECT_ROOT = find_project_root()


def get_data_dir() -> Path:
    override = os.getenv("PDF_SCHOOL_DATA_DIR")
    p = Path(override) if override else PROJECT_ROOT / "data"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_content_dir() -> Path:
    override = os.getenv("PDF_SCHOOL_CONTENT_DIR")
    p = Path(override) if override else PROJECT_ROOT / "content"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_sources_dir() -> Path:
    override = os.getenv("PDF_SCHOOL_SOURCES_DIR")
    p = Path(override) if override else PROJECT_ROOT / "sources"
    p.mkdir(parents=True, exist_ok=True)
    return p
