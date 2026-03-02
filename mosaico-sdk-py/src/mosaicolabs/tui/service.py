"""Read-only service layer for catalog extraction used by the TUI."""

from datetime import datetime, timezone
from typing import Dict, List

from mosaicolabs.comm import MosaicoClient
from mosaicolabs.logging_config import get_logger

from .view_models import CatalogSnapshot, SequenceSummary, TopicSummary

logger = get_logger(__name__)


class CatalogService:
    """Loads sequence/topic metadata snapshots from a remote Mosaico server."""

    def __init__(self, host: str, port: int, timeout: int = 5):
        self._host = host
        self._port = port
        self._timeout = timeout

    def load_catalog(self) -> CatalogSnapshot:
        """Fetches a complete catalog snapshot in a single client session."""
        sequence_summaries: List[SequenceSummary] = []
        topics_by_sequence: Dict[str, List[TopicSummary]] = {}
        errors: Dict[str, str] = {}

        with MosaicoClient.connect(
            host=self._host,
            port=self._port,
            timeout=self._timeout,
        ) as client:
            sequence_names = sorted(set(client.list_sequences()))

            for sequence_name in sequence_names:
                seq_handler = client.sequence_handler(sequence_name)
                if seq_handler is None:
                    message = "Unable to initialize SequenceHandler"
                    errors[sequence_name] = message
                    sequence_summaries.append(
                        SequenceSummary(
                            name=sequence_name,
                            created_datetime_utc=None,
                            total_size_bytes=0,
                            timestamp_ns_min=None,
                            timestamp_ns_max=None,
                            topics_count=0,
                            user_metadata={},
                            error=message,
                        )
                    )
                    topics_by_sequence[sequence_name] = []
                    continue

                try:
                    topic_summaries = self._load_topic_summaries(seq_handler, errors)

                    sequence_summaries.append(
                        SequenceSummary(
                            name=seq_handler.name,
                            created_datetime_utc=str(seq_handler.created_datetime),
                            total_size_bytes=seq_handler.total_size_bytes,
                            timestamp_ns_min=seq_handler.timestamp_ns_min,
                            timestamp_ns_max=seq_handler.timestamp_ns_max,
                            topics_count=len(topic_summaries),
                            user_metadata=seq_handler.user_metadata,
                            error=None,
                        )
                    )
                    topics_by_sequence[seq_handler.name] = sorted(
                        topic_summaries,
                        key=lambda topic: topic.name,
                    )

                finally:
                    # Close any topic handlers potentially spawned during the sweep.
                    seq_handler.close()

        return CatalogSnapshot(
            sequences=sequence_summaries,
            topics_by_sequence=topics_by_sequence,
            collected_at_utc=datetime.now(timezone.utc).isoformat(),
            errors=errors,
        )

    def _load_topic_summaries(self, seq_handler, errors: Dict[str, str]) -> List[TopicSummary]:
        topic_summaries: List[TopicSummary] = []

        for topic_name in seq_handler.topics:
            try:
                topic_handler = seq_handler.get_topic_handler(topic_name)
            except Exception as exc:
                err_key = f"{seq_handler.name}:{topic_name}"
                err_value = str(exc)
                errors[err_key] = err_value
                logger.error(
                    "Unable to load topic '%s' in sequence '%s': %s",
                    topic_name,
                    seq_handler.name,
                    exc,
                )
                topic_summaries.append(
                    TopicSummary(
                        name=topic_name,
                        ontology_tag=None,
                        serialization_format=None,
                        created_datetime_utc=None,
                        total_size_bytes=0,
                        timestamp_ns_min=None,
                        timestamp_ns_max=None,
                        user_metadata={},
                        error=err_value,
                    )
                )
                continue

            topic_summaries.append(
                TopicSummary(
                    name=topic_handler.name,
                    ontology_tag=topic_handler.ontology_tag,
                    serialization_format=topic_handler.serialization_format,
                    created_datetime_utc=str(topic_handler.created_datetime),
                    total_size_bytes=topic_handler.total_size_bytes,
                    timestamp_ns_min=topic_handler.timestamp_ns_min,
                    timestamp_ns_max=topic_handler.timestamp_ns_max,
                    user_metadata=topic_handler.user_metadata,
                    error=None,
                )
            )

        return topic_summaries
