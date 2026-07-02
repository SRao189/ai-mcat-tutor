"""Deterministic source ingestion for MCAT Tutor v2."""

from .service import IngestionService, ingest_source

__all__ = ["IngestionService", "ingest_source"]
