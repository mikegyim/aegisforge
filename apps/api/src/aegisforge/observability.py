"""Structured logging, metrics, and tracing wire-up."""

from __future__ import annotations

import logging
import sys

import structlog
from prometheus_client import Counter, Histogram

from .config import Settings


def configure_logging(settings: Settings) -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(stream=sys.stdout, level=level, format="%(message)s")

    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.log_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_tracing(settings: Settings, app) -> None:
    if not settings.enable_tracing or not settings.otlp_endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return

    provider = TracerProvider(resource=Resource.create({"service.name": settings.app_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


# Domain metrics ---------------------------------------------------------------
EVENTS_INGESTED = Counter(
    "aegisforge_events_ingested_total",
    "Number of infrastructure events ingested",
    labelnames=("event_type", "severity"),
)
INCIDENT_RISK = Histogram(
    "aegisforge_incident_risk_score",
    "Risk score of analyzed incidents",
    buckets=(10, 25, 50, 75, 90, 100),
)
LLM_LATENCY = Histogram(
    "aegisforge_llm_seconds",
    "LLM call latency",
    labelnames=("provider",),
)
PR_PROPOSED = Counter(
    "aegisforge_pr_proposed_total",
    "Pull requests proposed (including dry-runs)",
    labelnames=("dry_run",),
)
