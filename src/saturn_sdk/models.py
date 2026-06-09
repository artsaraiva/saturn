from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Fact:
    id: str
    subject: str
    predicate: str
    object: str
    source: str | None = None
    confidence: float = 0.8
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Fact:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Contradiction:
    id: str
    fact_a_id: str
    fact_b_id: str
    reason: str = ""
    score: float = 0.0
    state: str = "open"
    resolved_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Contradiction:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Revision:
    id: str
    entity_type: str
    entity_id: str
    change_type: str
    before: str | None = None
    after: str | None = None
    actor: str = ""
    timestamp: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Revision:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class HealthStatus:
    status: str
    schema_version: int | None = None
    fact_count: int = 0
    open_contradictions: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> HealthStatus:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
