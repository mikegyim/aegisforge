"""Persistent incident memory.

Stores every analysis the API produces and supports a lightweight similarity
search so the reasoning layer can ground new incidents in past ones. The
similarity is intentionally simple (token-overlap Jaccard over a normalized
keyword bag) - good enough to be useful, cheap enough that we don't need a
vector DB in the default deployment. The interface, however, is the right
shape to swap in pgvector + embeddings later.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool

from .models import IncidentAnalysis, SimilarIncident, utcnow


class Base(DeclarativeBase):
    pass


class IncidentRow(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), index=True)
    cluster: Mapped[str] = mapped_column(String(128), index=True)
    namespace: Mapped[str | None] = mapped_column(String(128), nullable=True)
    workload: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    signal: Mapped[str] = mapped_column(String(256), index=True)
    message: Mapped[str] = mapped_column(Text)
    keywords: Mapped[str] = mapped_column(Text)  # space-joined normalized tokens
    executive_summary: Mapped[str] = mapped_column(Text)
    root_cause: Mapped[str] = mapped_column(Text)
    plan_title: Mapped[str] = mapped_column(String(256))
    plan_risk: Mapped[str] = mapped_column(String(16))
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    analysis_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]+")
_STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "have", "has", "was",
    "were", "are", "but", "not", "you", "your", "our", "all", "any", "may",
    "kubernetes", "cluster", "event", "infrastructure",
}


def _tokenize(text: str) -> set[str]:
    return {
        t.lower() for t in _TOKEN_RE.findall(text)
        if len(t) > 2 and t.lower() not in _STOPWORDS
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class IncidentMemory:
    def __init__(self, database_url: str) -> None:
        # Allow callers to pass a sync URL; normalize to aiosqlite
        if database_url.startswith("sqlite:///") and "+aiosqlite" not in database_url:
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

        # For in-memory SQLite, each new connection is a fresh DB. Pin a
        # single shared connection via StaticPool so tables persist across
        # sessions (this is what makes the test fixtures work).
        engine_kwargs: dict[str, Any] = {"future": True}
        if ":memory:" in database_url:
            engine_kwargs["poolclass"] = StaticPool
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        self._engine = create_async_engine(database_url, **engine_kwargs)
        self._session: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine, expire_on_commit=False
        )

    async def init(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self._engine.dispose()

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session() as s:
            yield s

    async def remember(self, analysis: IncidentAnalysis) -> None:
        keywords = _tokenize(
            " ".join(
                [
                    analysis.event.signal,
                    analysis.event.message,
                    analysis.root_cause_hypothesis,
                    analysis.remediation_plan.title,
                ]
            )
        )
        row = IncidentRow(
            incident_id=analysis.incident_id,
            event_id=analysis.event.event_id,
            cluster=analysis.event.cluster,
            namespace=analysis.event.namespace,
            workload=analysis.event.workload,
            event_type=analysis.event.event_type.value,
            severity=analysis.event.severity.value,
            signal=analysis.event.signal,
            message=analysis.event.message,
            keywords=" ".join(sorted(keywords)),
            executive_summary=analysis.executive_summary,
            root_cause=analysis.root_cause_hypothesis,
            plan_title=analysis.remediation_plan.title,
            plan_risk=analysis.remediation_plan.risk,
            risk_score=max((f.risk_score for f in analysis.findings), default=0),
            confidence=max((f.confidence for f in analysis.findings), default=0.0),
            analysis_json=json.loads(analysis.model_dump_json()),
            created_at=analysis.created_at.replace(tzinfo=None),
        )
        async with self._session() as s:
            s.add(row)
            await s.commit()

    async def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        async with self._session() as s:
            res = await s.execute(
                select(IncidentRow).order_by(IncidentRow.created_at.desc()).limit(limit)
            )
            return [self._row_to_summary(r) for r in res.scalars().all()]

    async def get(self, incident_id: str) -> dict[str, Any] | None:
        async with self._session() as s:
            row = await s.get(IncidentRow, incident_id)
            return row.analysis_json if row else None

    async def find_similar(
        self,
        signal: str,
        message: str,
        cluster: str | None = None,
        top_k: int = 3,
        min_similarity: float = 0.15,
    ) -> list[SimilarIncident]:
        query_tokens = _tokenize(f"{signal} {message}")
        if not query_tokens:
            return []
        async with self._session() as s:
            stmt = select(IncidentRow).order_by(IncidentRow.created_at.desc()).limit(500)
            if cluster:
                stmt = stmt.where(IncidentRow.cluster == cluster)
            res = await s.execute(stmt)
            rows = res.scalars().all()

        scored: list[tuple[float, IncidentRow]] = []
        for row in rows:
            row_tokens = set(row.keywords.split()) if row.keywords else set()
            sim = _jaccard(query_tokens, row_tokens)
            if sim >= min_similarity:
                scored.append((sim, row))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            SimilarIncident(
                incident_id=row.incident_id,
                event_id=row.event_id,
                cluster=row.cluster,
                signal=row.signal,
                similarity=round(sim, 3),
                executive_summary=row.executive_summary,
                created_at=row.created_at,
            )
            for sim, row in scored[:top_k]
        ]

    @staticmethod
    def _row_to_summary(row: IncidentRow) -> dict[str, Any]:
        return {
            "incident_id": row.incident_id,
            "event_id": row.event_id,
            "cluster": row.cluster,
            "namespace": row.namespace,
            "workload": row.workload,
            "event_type": row.event_type,
            "severity": row.severity,
            "signal": row.signal,
            "plan_title": row.plan_title,
            "plan_risk": row.plan_risk,
            "risk_score": row.risk_score,
            "executive_summary": row.executive_summary,
            "created_at": row.created_at.isoformat(),
        }
