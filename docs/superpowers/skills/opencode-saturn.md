---
name: saturn
description: "Saturn memory quality engine — durable, curated fact storage for AI agents"
---

# Saturn Integration for OpenCode

Saturn is your persistent memory layer. Use it across sessions to avoid context bloat and contradictions.

## Quick start

```bash
# Init
saturn init

# Store context while working
saturn facts add --subject "Project" --predicate "uses" --object "React 18" --source "package.json" --confidence 0.95

# Query before starting a new task
saturn query "what does this project use?"
```

## MCP Tools (daemon required)

```bash
saturn daemon start
```

Then use MCP tools:
- `saturn_store_fact` — store a new fact
- `saturn_query` — query relevant context  
- `saturn_get_contradictions` — check for conflicts
- `saturn_resolve_contradiction` — resolve conflicts
- `saturn_maintain` — trigger curation pipeline
- `saturn_health` — memory stats

## Slash commands (shell)

```
saturn shell
  /search <terms>
  /show-fact <id>
  /contradictions
  /resolve <id> --action keep_a|keep_b|merge|dismiss|defer
  /doctor
  /exit
```

## Maintenance

Run daily or weekly:
```bash
saturn maintain run
saturn maintain run --dry-run
```

## Export

```bash
saturn export graph --format json -o knowledge-graph.json
saturn export graph --format dot | dot -Tsvg -o graph.svg
```

## Wiki

```bash
saturn wiki build
saturn wiki serve --port 8080
```

## Tips

- Use `--source` on every fact for provenance
- Resolve contradictions before they pile up
- `saturn doctor` checks workspace health
- The wiki is the human-readable view
