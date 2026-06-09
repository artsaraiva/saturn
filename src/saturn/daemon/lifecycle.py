from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from saturn.config import require_config


DAEMON_LOG = ".saturn/daemon.log"
DAEMON_PID = ".saturn/daemon.pid"


def _paths(project_root: Path) -> tuple[Path, Path]:
    return (
        project_root / DAEMON_PID,
        project_root / DAEMON_LOG,
    )


def start(project_root: Path, host: str = "127.0.0.1", port: int = 8468) -> str:
    config = require_config(project_root)
    pid_file, log_file = _paths(project_root)
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        if _pid_is_alive(pid):
            return f"Daemon already running (PID {pid})"

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn",
             "saturn.daemon.app:create_app",
             "--host", host,
             "--port", str(port),
             "--log-level", "info",
             "--factory"],
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=project_root,
        )
    pid_file.write_text(str(proc.pid))
    time.sleep(1)
    return f"Daemon started (PID {proc.pid}) on {host}:{port}"


def stop(project_root: Path) -> str:
    pid_file, _ = _paths(project_root)
    if not pid_file.exists():
        return "Daemon is not running"
    pid = int(pid_file.read_text().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            if not _pid_is_alive(pid):
                break
            time.sleep(0.5)
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    pid_file.unlink(missing_ok=True)
    return f"Daemon stopped (PID {pid})"


def status(project_root: Path) -> str:
    pid_file, _ = _paths(project_root)
    if not pid_file.exists():
        return "Daemon is not running"
    pid = int(pid_file.read_text().strip())
    if _pid_is_alive(pid):
        return f"Daemon is running (PID {pid})"
    pid_file.unlink(missing_ok=True)
    return "Daemon is not running (stale PID file cleaned up)"


def logs(project_root: Path, lines: int = 50) -> str:
    _, log_file = _paths(project_root)
    if not log_file.exists():
        return "No daemon log file found"
    content = log_file.read_text(encoding="utf-8")
    if not content.strip():
        return "(empty log)"
    all_lines = content.splitlines()
    tail = all_lines[-lines:]
    return "\n".join(tail)


def _pid_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
