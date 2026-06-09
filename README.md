![Saturn](docs/art/images/point_could_saturn_roman_god.png)

<p align="center">
  <strong>Memory quality OS for agents and teams.</strong><br>
  Harvest signal, weed noise. Memory that stays true over time.
</p>

---

## What is Saturn?

Saturn is a **memory quality engine + living wiki + graph layer** that sits behind AI agents and teams. It is not a vector database or a note-taking app. It is a curation engine that deduplicates facts, resolves contradictions, archives stale information, and projects everything into a human-readable wiki.

The problem: today's memory systems (vector DBs, chat histories) degrade over weeks. Duplicates accumulate, outdated facts persist, contradictions go unnoticed. Saturn actively maintains a clean, queryable knowledge base that improves with age.

## Core Capabilities

- **Structured facts** — Store (subject, predicate, object) triples with confidence and source tracking
- **Bulk ingestion** — Import facts from CSV, TSV, JSON, or plain text files
- **Revision tracking** — Every mutation creates an immutable audit trail
- **Contradiction detection** — Same subject + same predicate + different object = flagged automatically
- **Contradiction resolution** — Keep A, keep B, merge, dismiss, or defer
- **Workspace health** — Schema validation, database integrity checks, status reporting

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
git clone <your-repo-url>
cd saturn
uv pip install -e ".[dev]"
```

### Initialize a workspace

```bash
saturn init
```

This creates `.saturn/config.toml`, `.saturn/saturn.db`, and `docs/superpowers/project-status.*`.

### Add a fact

```bash
saturn facts add --subject "Saturn" --predicate "is" --object "a memory quality engine" --source "spec" --confidence 0.9
```

### Query facts

```bash
saturn query "Saturn"
```

### Ingest from a file

```bash
# CSV
saturn ingest data/facts.csv

# JSON
saturn ingest data/facts.json

# Directory (recursive)
saturn ingest data/

# Preview without storing
saturn ingest data/ --dry-run
```

### Detect and resolve contradictions

```bash
# Create two contradictory facts
saturn facts add --subject "Saturn" --predicate "is" --object "planet"
saturn facts add --subject "Saturn" --predicate "is" --object "star"

# List open contradictions
saturn contradictions list

# Keep the first fact, supersede the second
saturn contradictions resolve <contradiction-id> --action keep_a
```

### View revision history

```bash
saturn revisions list --entity-type fact
saturn revisions show <revision-id>
```

### Archive a fact

```bash
saturn facts archive <fact-id>
saturn query "Saturn" --include-archived
```

### Check workspace health

```bash
saturn doctor
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

## Phase 1 Status

**Implemented in Phase 1:**

- `saturn init`, `facts add`, `facts update`, `facts archive`
- `saturn query` with `--include-archived`
- `saturn doctor` with schema validation
- `saturn ingest` (CSV, TSV, JSON, TXT)
- `saturn contradictions list`, `saturn contradictions resolve`
- `saturn revisions list`, `saturn revisions show`
- Revision tracking on every mutation
- Rule-based contradiction detection and 5 resolution actions (keep_a, keep_b, merge, dismiss, defer)
- Schema migration from v1 to v2

**Phase 2 (planned):**

- REST API + MCP server for agent integration
- Interactive shell mode (`saturn shell`)
- Static wiki generation with backlinks
- Graph export
- Installable agent skills pack

## Architecture

```
CLI → config → db → facts → SQLite
                → revisions → SQLite
                → contradictions → SQLite
     → ingest → parser (CSV/TSV/JSON/TXT) → facts
     → doctor → schema validation → status docs
```

Built with Python 3.11+ and the standard library. No external dependencies for core functionality.

## License

MIT
