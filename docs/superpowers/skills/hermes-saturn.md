---
name: saturn
description: "Interact with Saturn memory quality engine — store, query, curate facts."
---

# Saturn Integration for Hermes

Use Saturn as your durable memory layer. Store facts, query curated context, manage contradictions.

## Prerequisites

- Saturn CLI installed (`pip install saturn`)
- Workspace initialized (`saturn init` in project root)
- Daemon running for SDK access (`saturn daemon start`)

## Commands

### Store a fact
```
saturn facts add --subject "X" --predicate "is/uses/has" --object "Y" --source "reason" --confidence 0.9
```

### Query facts
```
saturn query "what do I know about X?"
```

### Interactive shell
```
saturn shell
  /search <terms>
  /contradictions
  /resolve <id> --action keep_a|keep_b|merge|dismiss|defer
  /doctor
```

### Maintenance
```
saturn maintain run
saturn maintain run --dry-run
```

### Wiki
```
saturn wiki build
saturn wiki serve --port 8080
```

### Graph export
```
saturn export graph --format json --output graph.json
saturn export graph --format dot | dot -Tsvg -o graph.svg
```

## Best Practices

- Always specify `--source` so facts are traceable
- Run `saturn doctor` periodically to check workspace health
- Use `--confidence` to express certainty (0.0-1.0)
- Resolve contradictions promptly via `saturn contradictions resolve`
