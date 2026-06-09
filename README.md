<p align="center">
  <img src="docs/art/images/point_could_saturn_roman_god.png" alt="Saturn" width="100%">
</p>

<h1 align="center">Saturn</h1>

<p align="center">
  <strong>Memory quality OS for agents and teams.</strong><br>
  Harvest signal, weed noise. Memory that stays true over time.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat" alt="Python 3.11+"></a>
  <a href="#"><img src="https://img.shields.io/badge/Storage-SQLite-lightgrey?style=flat" alt="Storage: SQLite"></a>
</p>

<p align="center">
  <a href="#what-is-saturn">What</a> •
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#all-commands">Commands</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#license">License</a>
</p>

---

## What is Saturn?

Saturn is a **memory quality engine + living wiki + graph layer** that sits behind AI agents and teams. It is not a vector database or a note-taking app. It is a curation engine that deduplicates facts, resolves contradictions, archives stale information, and projects everything into a human-readable wiki.

The problem: today's memory systems (vector DBs, chat histories) degrade over weeks. Duplicates accumulate, outdated facts persist, contradictions go unnoticed. Saturn actively maintains a clean, queryable knowledge base that improves with age.

## Features

| Feature | Description |
|---------|-------------|
| **Structured facts** | Store (subject, predicate, object) triples with confidence and source tracking |
| **Bulk ingestion** | Import facts from CSV, TSV, JSON, or plain text files. Preview with `--dry-run`. |
| **Revision tracking** | Every mutation creates an immutable audit trail — who, what, when. |
| **Contradiction detection** | Same subject + same predicate + different object = flagged automatically. |
| **Contradiction resolution** | Five resolution actions: keep A, keep B, merge, dismiss, or defer. |
| **Workspace health** | Schema validation, database integrity checks, status reporting via `saturn doctor`. |
| **Zero heavy deps** | Python 3.11+ stdlib for core. SQLite for persistence. |
| **Agent-ready** | CLI-first design. Clean JSON output suitable for MCP tool wrapping. |

## Quick Start

### Install

```bash
git clone https://github.com/artsaraiva/saturn.git
cd saturn
uv pip install -e ".[dev]"
```

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/).

### First run

```bash
saturn init                           # initialize workspace
saturn facts add -s "Saturn" -p "is" -o "a memory quality engine"
saturn query "Saturn"                 # search your facts
saturn doctor                         # check workspace health
```

### Bulk ingest

```bash
saturn ingest data/facts.csv          # CSV
saturn ingest data/facts.json         # JSON
saturn ingest data/                   # directory (recursive)
saturn ingest data/ --dry-run         # preview without storing
```

### Detect and resolve contradictions

```bash
saturn contradictions list            # show all open contradictions
saturn contradictions resolve <id> --action keep_a
```

### View revisions

```bash
saturn revisions list --entity-type fact
saturn revisions show <revision-id>
```

## All Commands

| Command | Description |
|---|---|
| `saturn init` | Initialize a Saturn workspace |
| `saturn ingest <path>` | Bulk ingest facts from files |
| `saturn facts add` | Add a single fact |
| `saturn facts update <id>` | Update an existing fact |
| `saturn facts archive <id>` | Archive a fact |
| `saturn query <terms>` | Search stored facts |
| `saturn contradictions list` | List contradictions |
| `saturn contradictions resolve <id>` | Resolve a contradiction |
| `saturn revisions list` | View revision history |
| `saturn revisions show <id>` | View revision details |
| `saturn doctor` | Check workspace health |

## Roadmap

| Phase | Status | Deliverables |
|-------|--------|-------------|
| **Phase 1** | Done | `init`, `query`, `ingest`, `facts add/update/archive`, `contradictions list/resolve`, `revisions list/show`, `doctor`, schema v1→v2 migration, 5 contradiction resolution actions |
| **Phase 2** | Planned | REST API + MCP server, `saturn shell`, static wiki generation with backlinks, graph export, installable agent skills pack |

## Architecture

```
cli/
  commands/         init, facts, ingest, query, contradictions, revisions, doctor
core/
  database.py       SQLite connection + schema
  models.py         Fact, Revision, Contradiction data classes
  config.py         .saturn/config.toml reader
  ingest.py         CSV/TSV/JSON/TXT parser pipeline
  contradictions.py Detection + resolution logic
  doctor.py         Schema validation + health checks
```

Built with Python 3.11+ and the standard library. No external dependencies for core functionality. SQLite for persistence.

## Star History

<a href="https://star-history.com/#artsaraiva/saturn&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=artsaraiva/saturn&type=Date&theme=dark">
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=artsaraiva/saturn&type=Date">
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=artsaraiva/saturn&type=Date">
  </picture>
</a>

## License

MIT — see [LICENSE](LICENSE).
