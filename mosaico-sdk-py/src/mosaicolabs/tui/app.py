"""Textual app for browsing Mosaico catalog metadata."""

import json
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from .service import CatalogService
from .view_models import CatalogSnapshot, SequenceSummary, TopicSummary


class SequenceListItem(ListItem):
    """List item carrying a sequence summary payload."""

    def __init__(self, sequence: SequenceSummary):
        super().__init__(Label(sequence.name))
        self.sequence = sequence


class TopicListItem(ListItem):
    """List item carrying a topic summary payload."""

    def __init__(self, topic: TopicSummary):
        super().__init__(Label(topic.name))
        self.topic = topic


class MosaicoCatalogApp(App[None]):
    """Read-only catalog explorer for Mosaico sequences and topics."""

    CSS = """
    #main-body {
      height: 1fr;
    }

    #sequence-pane,
    #topic-pane,
    #details-pane {
      height: 1fr;
      border: solid $panel;
      padding: 0 1;
    }

    #sequence-pane {
      width: 1fr;
    }

    #topic-pane {
      width: 1fr;
    }

    #details-pane {
      width: 2fr;
    }

    .pane-title {
      height: 1;
      text-style: bold;
      color: $text;
    }

    #sequence-filter,
    #topic-filter {
      margin: 0 0 1 0;
    }

    #sequence-list,
    #topic-list {
      height: 1fr;
    }

    #details-content {
      height: 1fr;
      overflow: auto;
      color: $text;
    }

    #status {
      height: 1;
      color: $text-muted;
      padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("tab", "focus_next_pane", "Next Pane"),
        Binding("shift+tab", "focus_prev_pane", "Prev Pane"),
        Binding("escape", "clear_topic", "Back"),
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
    ]

    TITLE = "Mosaico Catalog"

    def __init__(self, *, host: str, port: int, timeout: int = 5):
        super().__init__()
        self._host = host
        self._port = port
        self._service = CatalogService(host=host, port=port, timeout=timeout)

        self._snapshot: Optional[CatalogSnapshot] = None
        self._selected_sequence: Optional[str] = None
        self._selected_topic: Optional[str] = None
        self._sequence_filter_text: str = ""
        self._topic_filter_text: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="main-body"):
            with Vertical(id="sequence-pane"):
                yield Static("Sequences", classes="pane-title")
                yield Input(placeholder="Filter sequences...", id="sequence-filter")
                yield ListView(id="sequence-list")

            with Vertical(id="topic-pane"):
                yield Static("Topics", classes="pane-title")
                yield Input(placeholder="Filter topics...", id="topic-filter")
                yield ListView(id="topic-list")

            with Vertical(id="details-pane"):
                yield Static("Details", classes="pane-title")
                yield Static(
                    "Press [r] to load the catalog.",
                    id="details-content",
                    markup=False,
                )

        yield Static("", id="status", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self._set_status(
            f"Target server: {self._host}:{self._port} | Press r to refresh catalog"
        )
        self.set_focus(self._sequence_filter_input)
        self.action_refresh()

    @property
    def _sequence_filter_input(self) -> Input:
        return self.query_one("#sequence-filter", Input)

    @property
    def _topic_filter_input(self) -> Input:
        return self.query_one("#topic-filter", Input)

    @property
    def _sequence_list(self) -> ListView:
        return self.query_one("#sequence-list", ListView)

    @property
    def _topic_list(self) -> ListView:
        return self.query_one("#topic-list", ListView)

    @property
    def _details(self) -> Static:
        return self.query_one("#details-content", Static)

    @property
    def _status(self) -> Static:
        return self.query_one("#status", Static)

    def action_refresh(self) -> None:
        self._set_status(f"Refreshing catalog from {self._host}:{self._port}...")
        self._refresh_catalog_worker()

    @work(thread=True, exclusive=True)
    def _refresh_catalog_worker(self) -> None:
        try:
            snapshot = self._service.load_catalog()
        except Exception as exc:
            self.call_from_thread(
                self._set_status,
                f"Refresh failed: {exc}",
                True,
            )
            return

        self.call_from_thread(self._apply_snapshot, snapshot)

    def _apply_snapshot(self, snapshot: CatalogSnapshot) -> None:
        previous_sequence = self._selected_sequence
        previous_topic = self._selected_topic

        self._snapshot = snapshot
        self._selected_sequence = None
        self._selected_topic = None

        visible_sequences = self._visible_sequences()
        self._populate_sequence_list(visible_sequences)

        if not visible_sequences:
            self._topic_list.clear()
            if snapshot.sequences:
                self._details.update("No sequences match the current sequence filter.")
            else:
                self._details.update("No sequences found on the server.")
            self._set_status(
                "Catalog loaded: "
                f"{len(snapshot.sequences)} total sequences, "
                f"0 visible, "
                f"{len(snapshot.errors)} warnings"
            )
            return

        target_sequence = previous_sequence
        if target_sequence is None or self._find_visible_sequence_summary(target_sequence) is None:
            target_sequence = visible_sequences[0].name

        self._select_sequence(target_sequence)
        self._set_sequence_cursor(target_sequence)

        if previous_topic is not None:
            self._restore_topic_selection(previous_topic)

        self._set_status(
            "Catalog loaded: "
            f"{len(snapshot.sequences)} total sequences, "
            f"{len(visible_sequences)} visible, "
            f"{len(snapshot.errors)} warnings"
        )

    def _visible_sequences(self) -> list[SequenceSummary]:
        if self._snapshot is None:
            return []

        needle = self._sequence_filter_text.strip().lower()
        if not needle:
            return self._snapshot.sequences

        return [
            summary
            for summary in self._snapshot.sequences
            if needle in summary.name.lower()
        ]

    def _visible_topics(self, sequence_name: str) -> list[TopicSummary]:
        if self._snapshot is None:
            return []

        topics = self._snapshot.topics_by_sequence.get(sequence_name, [])
        needle = self._topic_filter_text.strip().lower()
        if not needle:
            return topics

        return [
            summary
            for summary in topics
            if needle in summary.name.lower()
        ]

    def _populate_sequence_list(self, visible_sequences: list[SequenceSummary]) -> None:
        self._sequence_list.clear()

        for summary in visible_sequences:
            self._sequence_list.append(SequenceListItem(summary))

    def _populate_topic_list(self, sequence_name: str) -> None:
        self._topic_list.clear()

        for summary in self._visible_topics(sequence_name):
            self._topic_list.append(TopicListItem(summary))

    def _set_sequence_cursor(self, sequence_name: str) -> None:
        for index, child in enumerate(self._sequence_list.children):
            if isinstance(child, SequenceListItem) and child.sequence.name == sequence_name:
                self._sequence_list.index = index
                return

    def _set_topic_cursor(self, topic_name: str) -> None:
        for index, child in enumerate(self._topic_list.children):
            if isinstance(child, TopicListItem) and child.topic.name == topic_name:
                self._topic_list.index = index
                return

    def _find_sequence_summary(self, sequence_name: str) -> Optional[SequenceSummary]:
        if self._snapshot is None:
            return None

        for summary in self._snapshot.sequences:
            if summary.name == sequence_name:
                return summary
        return None

    def _find_visible_sequence_summary(
        self,
        sequence_name: str,
    ) -> Optional[SequenceSummary]:
        for summary in self._visible_sequences():
            if summary.name == sequence_name:
                return summary
        return None

    def _find_visible_topic_summary(
        self,
        sequence_name: str,
        topic_name: str,
    ) -> Optional[TopicSummary]:
        for summary in self._visible_topics(sequence_name):
            if summary.name == topic_name:
                return summary
        return None

    def _select_sequence(self, sequence_name: str) -> None:
        summary = self._find_visible_sequence_summary(sequence_name)
        if summary is None:
            return

        self._selected_sequence = summary.name
        self._selected_topic = None
        self._populate_topic_list(summary.name)
        self._render_sequence_details(summary)

    def _select_topic(self, topic_name: str) -> None:
        if self._selected_sequence is None:
            return

        summary = self._find_visible_topic_summary(self._selected_sequence, topic_name)
        if summary is None:
            return

        self._selected_topic = summary.name
        self._render_topic_details(summary)

    def _restore_topic_selection(self, topic_name: str) -> bool:
        if self._selected_sequence is None:
            return False

        summary = self._find_visible_topic_summary(self._selected_sequence, topic_name)
        if summary is None:
            return False

        self._selected_topic = summary.name
        self._set_topic_cursor(summary.name)
        self._render_topic_details(summary)
        return True

    @on(Input.Changed, "#sequence-filter")
    def _on_sequence_filter_changed(self, event: Input.Changed) -> None:
        self._sequence_filter_text = event.value

        visible_sequences = self._visible_sequences()
        previous_sequence = self._selected_sequence
        previous_topic = self._selected_topic

        self._populate_sequence_list(visible_sequences)

        if not visible_sequences:
            self._selected_sequence = None
            self._selected_topic = None
            self._topic_list.clear()
            self._details.update("No sequences match the current sequence filter.")
            self._set_status("Sequence filter applied: 0 visible rows")
            return

        target_sequence = previous_sequence
        if target_sequence is None or self._find_visible_sequence_summary(target_sequence) is None:
            target_sequence = visible_sequences[0].name

        self._select_sequence(target_sequence)
        self._set_sequence_cursor(target_sequence)

        if previous_topic is not None:
            self._restore_topic_selection(previous_topic)

        self._set_status(
            f"Sequence filter applied: {len(visible_sequences)} visible rows"
        )

    @on(Input.Changed, "#topic-filter")
    def _on_topic_filter_changed(self, event: Input.Changed) -> None:
        self._topic_filter_text = event.value

        if self._selected_sequence is None:
            self._topic_list.clear()
            self._set_status("Topic filter updated")
            return

        previous_topic = self._selected_topic
        self._populate_topic_list(self._selected_sequence)

        visible_topics = self._visible_topics(self._selected_sequence)

        restored = False
        if previous_topic is not None:
            restored = self._restore_topic_selection(previous_topic)

        if not restored:
            self._selected_topic = None
            summary = self._find_sequence_summary(self._selected_sequence)
            if summary is not None:
                self._render_sequence_details(summary)

        self._set_status(
            f"Topic filter applied: {len(visible_topics)} visible rows"
        )

    @on(Input.Submitted, "#sequence-filter")
    def _on_sequence_filter_submitted(self, _: Input.Submitted) -> None:
        self.set_focus(self._sequence_list)

    @on(Input.Submitted, "#topic-filter")
    def _on_topic_filter_submitted(self, _: Input.Submitted) -> None:
        self.set_focus(self._topic_list)

    @on(ListView.Highlighted, "#sequence-list")
    def _on_sequence_highlighted(self, event: ListView.Highlighted) -> None:
        item = event.item
        if not isinstance(item, SequenceListItem):
            return

        if item.sequence.name == self._selected_sequence:
            return

        self._select_sequence(item.sequence.name)

    @on(ListView.Highlighted, "#topic-list")
    def _on_topic_highlighted(self, event: ListView.Highlighted) -> None:
        if self.focused is not self._topic_list:
            return

        item = event.item
        if not isinstance(item, TopicListItem):
            return

        self._select_topic(item.topic.name)

    def action_clear_topic(self) -> None:
        if self._selected_sequence is None:
            return

        summary = self._find_sequence_summary(self._selected_sequence)
        if summary is None:
            return

        self._selected_topic = None
        self._render_sequence_details(summary)
        self._set_status(f"Showing sequence metadata for '{summary.name}'")

    def action_focus_next_pane(self) -> None:
        panes: list[Widget] = [
            self._sequence_filter_input,
            self._sequence_list,
            self._topic_filter_input,
            self._topic_list,
        ]
        self._focus_cycle(panes, forward=True)

    def action_focus_prev_pane(self) -> None:
        panes: list[Widget] = [
            self._sequence_filter_input,
            self._sequence_list,
            self._topic_filter_input,
            self._topic_list,
        ]
        self._focus_cycle(panes, forward=False)

    def _focus_cycle(self, panes: list[Widget], *, forward: bool) -> None:
        focused = self.focused

        if focused not in panes:
            self.set_focus(panes[0])
            return

        step = 1 if forward else -1
        current_index = panes.index(focused)
        next_index = (current_index + step) % len(panes)
        self.set_focus(panes[next_index])

    def action_cursor_down(self) -> None:
        self._move_cursor(+1)

    def action_cursor_up(self) -> None:
        self._move_cursor(-1)

    def _move_cursor(self, delta: int) -> None:
        focused = self.focused
        if not isinstance(focused, ListView):
            return

        children = [child for child in focused.children if isinstance(child, ListItem)]
        if not children:
            return

        current = focused.index if focused.index is not None else 0
        new_index = max(0, min(current + delta, len(children) - 1))
        focused.index = new_index

    def _set_status(self, message: str, is_error: bool = False) -> None:
        prefix = "ERROR" if is_error else "INFO"
        self._status.update(f"{prefix}: {message}")

    def _render_sequence_details(self, summary: SequenceSummary) -> None:
        lines = [
            f"Sequence: {summary.name}",
            f"Created: {summary.created_datetime_utc or 'n/a'}",
            f"Topics: {summary.topics_count}",
            f"Size: {self._format_size(summary.total_size_bytes)}",
            f"Timestamp range (ns): {self._format_ns(summary.timestamp_ns_min)} - {self._format_ns(summary.timestamp_ns_max)}",
            "",
            "User metadata:",
            self._format_json(summary.user_metadata),
        ]

        if summary.error:
            lines.extend(["", f"Warning: {summary.error}"])

        self._details.update("\n".join(lines))

    def _render_topic_details(self, summary: TopicSummary) -> None:
        lines = [
            f"Topic: {summary.name}",
            f"Ontology: {summary.ontology_tag or 'n/a'}",
            f"Serialization: {summary.serialization_format or 'n/a'}",
            f"Created: {summary.created_datetime_utc or 'n/a'}",
            f"Size: {self._format_size(summary.total_size_bytes)}",
            f"Timestamp range (ns): {self._format_ns(summary.timestamp_ns_min)} - {self._format_ns(summary.timestamp_ns_max)}",
            "",
            "User metadata:",
            self._format_json(summary.user_metadata),
        ]

        if summary.error:
            lines.extend(["", f"Warning: {summary.error}"])

        self._details.update("\n".join(lines))

    @staticmethod
    def _format_size(size_in_bytes: int) -> str:
        return f"{size_in_bytes / (1024 * 1024):.2f} MB"

    @staticmethod
    def _format_ns(timestamp_ns: Optional[int]) -> str:
        return "n/a" if timestamp_ns is None else str(timestamp_ns)

    @staticmethod
    def _format_json(metadata: dict) -> str:
        if not metadata:
            return "{}"
        return json.dumps(metadata, indent=2, sort_keys=True)
