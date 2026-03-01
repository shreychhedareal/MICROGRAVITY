"""Routing Mapper — learned query→agent/skill dispatch table.

Maintains a routing table that maps incoming queries to optimal
agent personas, tools, or skills based on historical success rates.

Architecture Rationale
─────────────────────
As the tool/skill catalogue grows, the LLM spends increasing tokens
"rediscovering" which tool fits which query.  A learned routing table
short-circuits this discovery by providing high-confidence route
suggestions before the LLM even starts reasoning.

The table updates itself after every interaction: successful routes
increase their confidence, failed routes decrease it.  This creates a
self-optimising dispatch layer without any manual configuration.

Complexity: MEDIUM
Necessity:  HIGH — directly reduces token waste and loop iterations
            for every message processed.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class RouteEntry:
    """A single route mapping a pattern to a target."""

    def __init__(
        self,
        pattern: str,
        target: str,
        target_type: str = "tool",
        embedding: list[float] | None = None,
    ):
        self.pattern = pattern
        self.target = target
        self.target_type = target_type  # "tool" | "skill" | "subagent"
        self.embedding = embedding
        self.call_count = 0
        self.success_count = 0
        self.last_used: str | None = None

    @property
    def success_rate(self) -> float:
        return self.success_count / max(1, self.call_count)

    def record_use(self, success: bool) -> None:
        self.call_count += 1
        if success:
            self.success_count += 1
        self.last_used = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "target": self.target,
            "target_type": self.target_type,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "success_rate": round(self.success_rate, 3),
            "last_used": self.last_used,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RouteEntry:
        entry = cls(
            pattern=data["pattern"],
            target=data["target"],
            target_type=data.get("target_type", "tool"),
        )
        entry.call_count = data.get("call_count", 0)
        entry.success_count = data.get("success_count", 0)
        entry.last_used = data.get("last_used")
        return entry


class RoutingMapper:
    """Self-improving query→target dispatch table.

    Routes are matched by exact pattern first, then by semantic
    similarity (if embeddings are available).  The routing table
    is persisted and updated after every interaction.
    """

    def __init__(self, workspace: Path, auto_dispatch_threshold: float = 0.8):
        self._path = workspace / "processors" / "routing_table.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._threshold = auto_dispatch_threshold
        self._routes: list[RouteEntry] = []
        self._load()

    # ── Persistence ────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._routes = [RouteEntry.from_dict(r) for r in data.get("routes", [])]
        except Exception as e:
            logger.warning("RoutingMapper load error: {}", e)

    def _save(self) -> None:
        payload = {
            "updated_at": datetime.now().isoformat(),
            "routes": [r.to_dict() for r in self._routes],
        }
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ── Route Management ───────────────────────────────────────────

    def add_route(
        self,
        pattern: str,
        target: str,
        target_type: str = "tool",
        embedding: list[float] | None = None,
    ) -> RouteEntry:
        """Register a new route pattern."""
        entry = RouteEntry(pattern, target, target_type, embedding)
        self._routes.append(entry)
        self._save()
        logger.info("Route added: '{}' → {} ({})", pattern[:40], target, target_type)
        return entry

    def remove_route(self, pattern: str) -> bool:
        before = len(self._routes)
        self._routes = [r for r in self._routes if r.pattern != pattern]
        if len(self._routes) < before:
            self._save()
            return True
        return False

    # ── Matching ───────────────────────────────────────────────────

    def find_routes(self, query: str, embedding: list[float] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        """Find matching routes for a query.

        Returns routes sorted by success_rate, annotated with match type.
        """
        matches: list[dict[str, Any]] = []

        # Exact substring matching
        query_lower = query.lower()
        for route in self._routes:
            if route.pattern.lower() in query_lower or query_lower in route.pattern.lower():
                matches.append({
                    "route": route,
                    "match_type": "exact",
                    "confidence": route.success_rate,
                })

        # Semantic matching (if embeddings available)
        if embedding and not matches:
            try:
                import numpy as np
                query_vec = np.array(embedding, dtype=np.float32)
                norm_q = np.linalg.norm(query_vec)
                if norm_q > 0:
                    for route in self._routes:
                        if route.embedding is None:
                            continue
                        route_vec = np.array(route.embedding, dtype=np.float32)
                        norm_r = np.linalg.norm(route_vec)
                        if norm_r == 0:
                            continue
                        sim = float(np.dot(query_vec, route_vec) / (norm_q * norm_r))
                        if sim > 0.7:
                            matches.append({
                                "route": route,
                                "match_type": "semantic",
                                "confidence": sim * route.success_rate,
                            })
            except ImportError:
                pass

        matches.sort(key=lambda m: -m["confidence"])
        return matches[:top_k]

    def should_auto_dispatch(self, query: str, embedding: list[float] | None = None) -> RouteEntry | None:
        """Return a route for auto-dispatch if confidence exceeds threshold."""
        matches = self.find_routes(query, embedding, top_k=1)
        if matches and matches[0]["confidence"] >= self._threshold:
            return matches[0]["route"]
        return None

    def record_outcome(self, pattern: str, success: bool) -> None:
        """Update route stats after an interaction."""
        for route in self._routes:
            if route.pattern == pattern:
                route.record_use(success)
                break
        self._save()

    # ── Introspection ──────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        total_calls = sum(r.call_count for r in self._routes)
        total_success = sum(r.success_count for r in self._routes)
        return {
            "total_routes": len(self._routes),
            "total_calls": total_calls,
            "overall_success_rate": round(total_success / max(1, total_calls), 3),
        }

    def render_status(self) -> str:
        s = self.get_stats()
        lines = [
            "=== ROUTING MAPPER STATUS ===",
            f"Routes: {s['total_routes']}  Total calls: {s['total_calls']}",
            f"Overall success: {s['overall_success_rate']:.1%}",
        ]
        top = sorted(self._routes, key=lambda r: -r.call_count)[:5]
        if top:
            lines.append("\nTop routes:")
            for r in top:
                lines.append(f"  '{r.pattern[:30]}' → {r.target} ({r.success_rate:.0%}, {r.call_count} calls)")
        return "\n".join(lines)
