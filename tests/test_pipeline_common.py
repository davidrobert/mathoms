#!/usr/bin/env python3
"""Tests for the shared pipeline_common module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.pipeline_common import (
    PROJECT_DIR, CONFIG_DIR, safe_float, load_json_config,
)


class TestPaths:
    def test_project_dir_exists(self):
        assert PROJECT_DIR.exists()

    def test_config_dir_exists(self):
        assert CONFIG_DIR.exists()


class TestSafeFloat:
    def test_int(self):
        assert safe_float(42) == 42.0

    def test_float(self):
        assert safe_float(3.14) == 3.14

    def test_string_plain(self):
        assert safe_float("123.45") == 123.45

    def test_string_brazilian(self):
        assert safe_float("1.234,56") == 1234.56

    def test_none(self):
        assert safe_float(None) == 0.0

    def test_none_custom_default(self):
        assert safe_float(None, default=-1.0) == -1.0

    def test_empty_string(self):
        assert safe_float("") == 0.0

    def test_garbage(self):
        assert safe_float("abc") == 0.0


class TestLoadJsonConfig:
    def test_existing_config(self):
        data = load_json_config("pipeline.json")
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_nonexistent_config(self):
        data = load_json_config("nonexistent_file_xyz.json")
        assert data == {}

    def test_required_nonexistent_raises(self):
        try:
            load_json_config("nonexistent_file_xyz.json", required=True)
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass
