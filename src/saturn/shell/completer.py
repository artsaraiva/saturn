from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion

from saturn.config import load_config, WorkspaceNotInitializedError
from saturn.db import connect

SHELL_COMMANDS = {
    "search",
    "show-fact",
    "contradictions",
    "resolve",
    "merge",
    "archive",
    "explain-why",
    "trace-source",
    "help",
    "exit",
    "quit",
    "doctor",
}


class SaturnCompleter(Completer):
    def __init__(self, workspace: object) -> None:
        self.workspace = workspace

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        if text.startswith("/"):
            parts = text[1:].split()
            if len(parts) == 1 and not text.endswith(" "):
                partial = parts[0].lower()
                for cmd in sorted(SHELL_COMMANDS):
                    if cmd.startswith(partial):
                        yield Completion(f"/{cmd}", start_position=-len(text))

            elif text.startswith("/resolve ") and len(parts) >= 2:
                partial = parts[-1] if not text.endswith(" ") else ""
                for cid in self._get_contradiction_ids():
                    if cid.startswith(partial):
                        yield Completion(cid, start_position=(-len(partial) if partial else 0))

            elif text.startswith("/show-fact ") and len(parts) >= 2:
                partial = parts[-1] if not text.endswith(" ") else ""
                for fid in self._get_fact_ids():
                    if fid.startswith(partial):
                        yield Completion(fid, start_position=(-len(partial) if partial else 0))

            elif text.startswith("/archive ") and len(parts) >= 2:
                partial = parts[-1] if not text.endswith(" ") else ""
                for fid in self._get_fact_ids():
                    if fid.startswith(partial):
                        yield Completion(fid, start_position=(-len(partial) if partial else 0))

            elif text.startswith("/explain-why ") and len(parts) >= 2:
                partial = parts[-1] if not text.endswith(" ") else ""
                for cid in self._get_contradiction_ids():
                    if cid.startswith(partial):
                        yield Completion(cid, start_position=(-len(partial) if partial else 0))

            elif text.startswith("/trace-source ") and len(parts) >= 2:
                partial = parts[-1] if not text.endswith(" ") else ""
                for fid in self._get_fact_ids():
                    if fid.startswith(partial):
                        yield Completion(fid, start_position=(-len(partial) if partial else 0))

            elif text.startswith("/merge approve ") and len(parts) >= 3:
                partial = parts[-1] if not text.endswith(" ") else ""
                for gid in self._get_merge_group_ids():
                    if gid.startswith(partial):
                        yield Completion(gid, start_position=(-len(partial) if partial else 0))

            elif text.startswith("/merge reject ") and len(parts) >= 2:
                partial = parts[-1] if not text.endswith(" ") else ""
                for gid in self._get_merge_group_ids():
                    if gid.startswith(partial):
                        yield Completion(gid, start_position=(-len(partial) if partial else 0))

    def _get_merge_group_ids(self) -> list[str]:
        try:
            config = load_config(self.workspace)
            with connect(config.db_path) as conn:
                rows = conn.execute(
                    "SELECT id FROM merge_groups WHERE canonical_fact_id IS NULL AND merge_strategy IS NULL "
                    "ORDER BY created_at DESC LIMIT 20"
                ).fetchall()
                return [r["id"] for r in rows]
        except Exception:
            return []

    def _get_fact_ids(self) -> list[str]:
        try:
            config = load_config(self.workspace)
            with connect(config.db_path) as conn:
                rows = conn.execute(
                    "SELECT id FROM facts ORDER BY created_at DESC LIMIT 100"
                ).fetchall()
                return [r["id"] for r in rows]
        except Exception:
            return []

    def _get_contradiction_ids(self) -> list[str]:
        try:
            config = load_config(self.workspace)
            with connect(config.db_path) as conn:
                rows = conn.execute(
                    "SELECT id FROM contradictions ORDER BY resolved_at DESC LIMIT 50"
                ).fetchall()
                return [r["id"] for r in rows]
        except Exception:
            return []
