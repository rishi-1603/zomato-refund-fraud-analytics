"""Regression: the dashboard must find its data regardless of the working directory."""
import importlib.util
import os
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


def _load_app():
    spec = importlib.util.spec_from_file_location("zomato_app_paths", APP)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_data_paths_are_absolute_and_exist(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # run from an unrelated directory
    app = _load_app()
    for path in (app.DATA_PATH, app.TRUTH_PATH, app.METRICS_PATH):
        assert os.path.isabs(path), path
        assert os.path.exists(path), path


def test_no_relative_data_reads_remain_in_app():
    source = APP.read_text(encoding="utf-8")
    assert 'read_csv("data/' not in source
    assert "read_csv('data/" not in source
