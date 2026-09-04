import os
from unittest.mock import patch

from pdf_school.core.config import find_project_root, get_content_dir, get_data_dir, get_sources_dir


def test_find_project_root():
    root = find_project_root()
    assert root.exists()
    assert (root / "pyproject.toml").exists() or (root / ".git").exists()


def test_get_dirs_default():
    with patch.dict(os.environ, {}, clear=True):
        data_dir = get_data_dir()
        assert data_dir.name == "data"
        assert data_dir.exists()

        content_dir = get_content_dir()
        assert content_dir.name == "content"
        assert content_dir.exists()

        sources_dir = get_sources_dir()
        assert sources_dir.name == "sources"
        assert sources_dir.exists()


def test_get_dirs_override(tmp_path):
    custom_data = tmp_path / "custom_data"
    custom_content = tmp_path / "custom_content"
    custom_sources = tmp_path / "custom_sources"

    env = {
        "PDF_SCHOOL_DATA_DIR": str(custom_data),
        "PDF_SCHOOL_CONTENT_DIR": str(custom_content),
        "PDF_SCHOOL_SOURCES_DIR": str(custom_sources),
    }

    with patch.dict(os.environ, env, clear=True):
        assert get_data_dir() == custom_data
        assert custom_data.exists()
        assert get_content_dir() == custom_content
        assert custom_content.exists()
        assert get_sources_dir() == custom_sources
        assert custom_sources.exists()
