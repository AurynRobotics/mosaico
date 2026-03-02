"""View models for the Mosaico catalog TUI."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TopicSummary:
    """UI-friendly snapshot of a topic and its metadata."""

    name: str
    ontology_tag: Optional[str]
    serialization_format: Optional[str]
    created_datetime_utc: Optional[str]
    total_size_bytes: int
    timestamp_ns_min: Optional[int]
    timestamp_ns_max: Optional[int]
    user_metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass(frozen=True)
class SequenceSummary:
    """UI-friendly snapshot of a sequence and its metadata."""

    name: str
    created_datetime_utc: Optional[str]
    total_size_bytes: int
    timestamp_ns_min: Optional[int]
    timestamp_ns_max: Optional[int]
    topics_count: int
    user_metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass(frozen=True)
class CatalogSnapshot:
    """A complete in-memory catalog snapshot used by the TUI."""

    sequences: List[SequenceSummary]
    topics_by_sequence: Dict[str, List[TopicSummary]]
    collected_at_utc: str
    errors: Dict[str, str] = field(default_factory=dict)
