from __future__ import annotations

# Backward-compatible import surface. V0.47a moved the actual registry to
# lore_catalog.py so the same source manifest can carry audit state, periods,
# categories and official references without breaking existing imports.
from .lore_catalog import (  # noqa: F401
    AUDIT_STATUSES,
    PARIS_BY_NIGHT_PAGES,
    PARIS_BY_NIGHT_ROOT,
    PARIS_CORPUS_SOURCES,
    SOURCE_TIERS,
    WOD_RPG_ERA_MODEL,
    LoreSourceRef,
    corpus_audit_report,
    lore_source,
    sources_for_year,
    validate_source_catalog,
)

__all__ = [
    "AUDIT_STATUSES",
    "PARIS_BY_NIGHT_PAGES",
    "PARIS_BY_NIGHT_ROOT",
    "PARIS_CORPUS_SOURCES",
    "SOURCE_TIERS",
    "WOD_RPG_ERA_MODEL",
    "LoreSourceRef",
    "corpus_audit_report",
    "lore_source",
    "sources_for_year",
    "validate_source_catalog",
]
