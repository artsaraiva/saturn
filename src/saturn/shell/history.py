from __future__ import annotations

from pathlib import Path

from prompt_toolkit.history import FileHistory, History


SHELL_HISTORY_FILE = ".saturn/shell_history"


def load_history(workspace_dir: Path) -> History:
    history_path = workspace_dir / ".." / SHELL_HISTORY_FILE
    return FileHistory(str(history_path))
