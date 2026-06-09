from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


SCHEMA_VERSION = 3


class WorkspaceNotInitializedError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkspaceConfig:
    project_root: Path
    workspace_dir: Path
    config_path: Path
    db_path: Path
    schema_version: int


def resolve_workspace(project_root: Path) -> WorkspaceConfig:
    workspace_dir = project_root / ".saturn"
    config_path = workspace_dir / "config.toml"
    db_path = workspace_dir / "saturn.db"
    return WorkspaceConfig(project_root, workspace_dir, config_path, db_path, SCHEMA_VERSION)


def write_default_config(config: WorkspaceConfig) -> None:
    config.workspace_dir.mkdir(parents=True, exist_ok=True)
    config.config_path.write_text(
        'schema_version = 3\n'
        'db_path = ".saturn/saturn.db"\n'
        'project_root = "."\n',
        encoding="utf-8",
    )


def load_config(project_root: Path) -> WorkspaceConfig:
    config = resolve_workspace(project_root)
    try:
        data = tomllib.loads(config.config_path.read_text(encoding="utf-8"))
        return WorkspaceConfig(
            project_root=project_root,
            workspace_dir=config.workspace_dir,
            config_path=config.config_path,
            db_path=project_root / data["db_path"],
            schema_version=SCHEMA_VERSION,
        )
    except (tomllib.TOMLDecodeError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid config at {config.config_path}") from error


def require_config(project_root: Path) -> WorkspaceConfig:
    config = resolve_workspace(project_root)
    if not config.config_path.exists():
        raise WorkspaceNotInitializedError(
            "Workspace is not initialized. Run `saturn init` first."
        )
    return load_config(project_root)
