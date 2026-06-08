from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from saturn.config import WorkspaceConfig, require_config
from saturn.db import connect, require_initialized_database
from saturn.facts import FactInput, build_fact_input, insert_fact

SUPPORTED_FORMATS = {"csv", "tsv", "json", "txt"}
EXTENSION_MAP: dict[str, str] = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".json": "json",
    ".txt": "txt",
}


@dataclass(frozen=True)
class IngestStats:
    total_files: int = 0
    total_facts: int = 0
    errors: int = 0
    skipped: int = 0


@dataclass(frozen=True)
class IngestResult:
    stats: IngestStats
    messages: list[str]


def detect_format(path: Path, force_format: str | None) -> str:
    if force_format:
        if force_format not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{force_format}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )
        return force_format
    ext = path.suffix.lower()
    fmt = EXTENSION_MAP.get(ext)
    if fmt is None:
        raise ValueError(
            f"Unsupported file extension '{ext}' for {path.name}. "
            f"Supported: {', '.join(EXTENSION_MAP.keys())}"
        )
    return fmt


def parse_csv(file: IO[str], source_override: str | None) -> list[FactInput]:
    reader = csv.DictReader(file)
    if not reader.fieldnames:
        raise ValueError("CSV file has no header row")

    required = {"subject", "predicate", "object"}
    missing = required - set(reader.fieldnames)
    if missing:
        raise ValueError(
            f"CSV missing required columns: {', '.join(sorted(missing))}"
        )

    facts: list[FactInput] = []
    for row_num, row in enumerate(reader, start=2):
        source = source_override or row.get("source") or None
        confidence = row.get("confidence")
        try:
            facts.append(
                build_fact_input(
                    subject=row["subject"],
                    predicate=row["predicate"],
                    object_=row["object"],
                    source=source,
                    confidence=float(confidence) if confidence else None,
                )
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Row {row_num}: {e}") from e
    return facts


def parse_tsv(file: IO[str], source_override: str | None) -> list[FactInput]:
    reader = csv.DictReader(file, delimiter="\t")
    if not reader.fieldnames:
        raise ValueError("TSV file has no header row")

    required = {"subject", "predicate", "object"}
    missing = required - set(reader.fieldnames)
    if missing:
        raise ValueError(
            f"TSV missing required columns: {', '.join(sorted(missing))}"
        )

    facts: list[FactInput] = []
    for row_num, row in enumerate(reader, start=2):
        source = source_override or row.get("source") or None
        confidence = row.get("confidence")
        try:
            facts.append(
                build_fact_input(
                    subject=row["subject"],
                    predicate=row["predicate"],
                    object_=row["object"],
                    source=source,
                    confidence=float(confidence) if confidence else None,
                )
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Row {row_num}: {e}") from e
    return facts


def parse_json(file: IO[str], source_override: str | None) -> list[FactInput]:
    data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("JSON file must contain an array of fact objects")

    facts: list[FactInput] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx}: expected an object, got {type(item).__name__}")

        missing = {"subject", "predicate", "object"} - set(item.keys())
        if missing:
            raise ValueError(
                f"Item {idx}: missing required keys: {', '.join(sorted(missing))}"
            )

        source = source_override or item.get("source") or None
        confidence = item.get("confidence")
        try:
            facts.append(
                build_fact_input(
                    subject=item["subject"],
                    predicate=item["predicate"],
                    object_=item["object"],
                    source=source,
                    confidence=float(confidence) if confidence is not None else None,
                )
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Item {idx}: {e}") from e
    return facts


def parse_text(file: IO[str], filename_stem: str, source_override: str | None) -> list[FactInput]:
    lines = [line.strip() for line in file if line.strip()]
    source = source_override or filename_stem
    facts: list[FactInput] = []
    for line in lines:
        facts.append(
            build_fact_input(
                subject=filename_stem,
                predicate="contains",
                object_=line,
                source=source,
                confidence=None,
            )
        )
    return facts


PARSERS = {
    "csv": parse_csv,
    "tsv": parse_tsv,
    "json": parse_json,
    "txt": parse_text,
}


def ingest_path(
    path: Path,
    *,
    source: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    format: str | None = None,
    config: WorkspaceConfig,
) -> IngestResult:
    require_initialized_database(config.db_path, config.schema_version)

    if path.is_dir():
        return _ingest_directory(path, source=source, dry_run=dry_run, verbose=verbose, format=format, config=config)
    else:
        return _ingest_file(path, source=source, dry_run=dry_run, verbose=verbose, format=format, config=config)


def _ingest_directory(
    directory: Path,
    *,
    source: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    format: str | None = None,
    config: WorkspaceConfig,
) -> IngestResult:
    stats = IngestStats()
    messages: list[str] = []

    files = sorted(
        p for p in directory.rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSION_MAP
    )

    if not files:
        messages.append(f"No supported files found in {directory}")
        return IngestResult(stats, messages)

    stats = IngestStats(total_files=len(files))

    for file_path in files:
        result = _ingest_file(
            file_path, source=source, dry_run=dry_run,
            verbose=verbose, format=format, config=config,
        )
        messages.extend(result.messages)
        stats = IngestStats(
            total_files=stats.total_files,
            total_facts=stats.total_facts + result.stats.total_facts,
            errors=stats.errors + result.stats.errors,
            skipped=stats.skipped + result.stats.skipped,
        )

    return IngestResult(stats, messages)


def _ingest_file(
    file_path: Path,
    *,
    source: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    format: str | None = None,
    config: WorkspaceConfig,
) -> IngestResult:
    messages: list[str] = []

    try:
        fmt = detect_format(file_path, format)
    except ValueError as e:
        messages.append(f"SKIP {file_path}: {e}")
        return IngestResult(IngestStats(total_files=1, skipped=1), messages)

    try:
        with file_path.open("r", encoding="utf-8") as f:
            parser = PARSERS[fmt]
            if fmt == "txt":
                filename_stem = file_path.stem
                facts = parser(f, filename_stem, source)
            else:
                facts = parser(f, source)
    except (ValueError, json.JSONDecodeError, csv.Error) as e:
        messages.append(f"ERROR {file_path}: {e}")
        return IngestResult(IngestStats(total_files=1, errors=1), messages)
    except OSError as e:
        messages.append(f"ERROR {file_path}: {e}")
        return IngestResult(IngestStats(total_files=1, errors=1), messages)

    if not facts:
        messages.append(f"EMPTY {file_path}: No facts found")
        return IngestResult(IngestStats(total_files=1, skipped=1), messages)

    if dry_run:
        messages.append(f"DRY-RUN {file_path}: {len(facts)} fact(s) would be stored")
        if verbose:
            for fact in facts:
                messages.append(f"  {fact.subject} | {fact.predicate} | {fact.object}")
        return IngestResult(IngestStats(total_files=1, total_facts=len(facts)), messages)

    try:
        with connect(config.db_path) as connection:
            stored_ids: list[str] = []
            for fact in facts:
                fact_id = insert_fact(connection, fact)
                stored_ids.append(fact_id)

        if verbose:
            messages.append(f"STORED {file_path}: {len(facts)} fact(s)")
            for fact_id, fact in zip(stored_ids, facts):
                messages.append(f"  {fact_id[:8]} | {fact.subject} | {fact.predicate} | {fact.object}")
        else:
            messages.append(f"STORED {file_path}: {len(facts)} fact(s)")

        return IngestResult(IngestStats(total_files=1, total_facts=len(stored_ids)), messages)
    except Exception as e:
        messages.append(f"ERROR {file_path}: Database write failed: {e}")
        return IngestResult(IngestStats(total_files=1, errors=1), messages)


def run_ingest(
    path_str: str,
    *,
    source: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
    format: str | None = None,
    config: WorkspaceConfig,
) -> IngestResult:
    path = Path(path_str).resolve()
    if not path.exists():
        return IngestResult(
            IngestStats(errors=1),
            [f"ERROR {path}: path does not exist"],
        )

    return ingest_path(
        path,
        source=source,
        dry_run=dry_run,
        verbose=verbose,
        format=format,
        config=config,
    )
