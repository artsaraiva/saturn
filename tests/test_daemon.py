import time
from pathlib import Path
from saturn.config import resolve_workspace, write_default_config, load_config
from saturn.db import initialize_database
from saturn.daemon.lifecycle import start, stop, status, logs


def test_start_stop(tmp_path):
    _init(tmp_path)
    result = start(tmp_path, port=18468)
    assert "started" in result
    assert "18468" in result
    time.sleep(1)
    status_result = status(tmp_path)
    assert "running" in status_result
    stop_result = stop(tmp_path)
    assert "stopped" in stop_result
    time.sleep(0.5)
    status_result2 = status(tmp_path)
    assert "not running" in status_result2


def test_status_not_running(tmp_path):
    _init(tmp_path)
    result = status(tmp_path)
    assert "not running" in result


def test_logs(tmp_path):
    _init(tmp_path)
    result = start(tmp_path, port=18469)
    assert "started" in result
    time.sleep(2)
    log_content = logs(tmp_path)
    assert log_content != "(empty log)"
    stop(tmp_path)


def _init(tmp_path: Path):
    workspace = resolve_workspace(tmp_path)
    write_default_config(workspace)
    config = load_config(tmp_path)
    initialize_database(config.db_path, config.schema_version)
