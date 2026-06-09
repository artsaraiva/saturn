from __future__ import annotations

from typing import Any

import httpx

from saturn_sdk.models import Contradiction, Fact, HealthStatus, Revision


class SaturnClient:
    """Python client for the Saturn REST API."""

    def __init__(self, base_url: str = "http://localhost:8468", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    # --- Health ---

    def health(self) -> HealthStatus:
        resp = self._client.get(f"{self.base_url}/api/health")
        resp.raise_for_status()
        return HealthStatus.from_dict(resp.json())

    # --- Facts ---

    def create_fact(self, subject: str, predicate: str, object: str,
                    source: str | None = None, confidence: float | None = None) -> Fact:
        body = {"subject": subject, "predicate": predicate, "object": object}
        if source is not None:
            body["source"] = source
        if confidence is not None:
            body["confidence"] = confidence
        resp = self._client.post(f"{self.base_url}/api/facts", json=body)
        resp.raise_for_status()
        return Fact.from_dict(resp.json())

    def list_facts(self, status: str | None = None, limit: int = 100) -> list[Fact]:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        resp = self._client.get(f"{self.base_url}/api/facts", params=params)
        resp.raise_for_status()
        return [Fact.from_dict(f) for f in resp.json()]

    def get_fact(self, fact_id: str) -> Fact:
        resp = self._client.get(f"{self.base_url}/api/facts/{fact_id}")
        resp.raise_for_status()
        return Fact.from_dict(resp.json())

    def update_fact(self, fact_id: str, **kwargs) -> Fact:
        resp = self._client.patch(f"{self.base_url}/api/facts/{fact_id}", json=kwargs)
        resp.raise_for_status()
        return Fact.from_dict(resp.json())

    def archive_fact(self, fact_id: str) -> Fact:
        resp = self._client.post(f"{self.base_url}/api/facts/{fact_id}/archive")
        resp.raise_for_status()
        return Fact.from_dict(resp.json())

    # --- Query ---

    def query(self, terms: str, include_archived: bool = False) -> list[Fact]:
        params: dict[str, Any] = {"terms": terms}
        if include_archived:
            params["include_archived"] = "true"
        resp = self._client.get(f"{self.base_url}/api/query", params=params)
        resp.raise_for_status()
        return [Fact.from_dict(f) for f in resp.json()]

    # --- Contradictions ---

    def list_contradictions(self, all_: bool = False) -> list[Contradiction]:
        params = {} if all_ else {"state": "open"}
        resp = self._client.get(f"{self.base_url}/api/contradictions", params=params)
        resp.raise_for_status()
        return [Contradiction.from_dict(c) for c in resp.json()]

    def resolve_contradiction(self, contradiction_id: str, action: str,
                              merged_object: str | None = None) -> dict:
        body = {"action": action}
        if merged_object:
            body["object"] = merged_object
        resp = self._client.post(f"{self.base_url}/api/contradictions/{contradiction_id}/resolve", json=body)
        resp.raise_for_status()
        return resp.json()

    # --- Revisions ---

    def list_revisions(self, entity_type: str | None = None,
                       entity_id: str | None = None, limit: int = 50) -> list[Revision]:
        params: dict[str, Any] = {"limit": limit}
        if entity_type:
            params["entity_type"] = entity_type
        if entity_id:
            params["entity_id"] = entity_id
        resp = self._client.get(f"{self.base_url}/api/revisions", params=params)
        resp.raise_for_status()
        return [Revision.from_dict(r) for r in resp.json()]

    # --- Context manager support ---

    def __enter__(self) -> SaturnClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()
