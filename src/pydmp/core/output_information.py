"""Stateless `?Zi` output-information transaction and reply parsing.

Lowercase `?Zi` is distinct from uppercase `?ZI`. For normal numeric outputs it
returns Output Information rows: output name plus Output Real-Time Status. The
same page family can also expose backend-linked rows with serial/supervision
fields; those fields are preserved without over-interpreting the product type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .errors import SessionProtocolError
from .models import (
    PanelEndpoint,
    Transaction,
    TransactionRunner,
    payload_required,
)

OUTPUT_INFORMATION_RECORD_SEPARATOR: Final[bytes] = b"\x1e"
OUTPUT_INFORMATION_REPLY_PREFIXES: Final[tuple[bytes, ...]] = (
    b"*Zi",
    b"!Zi",
    b"?Zi",
)
OUTPUT_INFORMATION_PAGE_TERMINATOR: Final[bytes] = b"----"
OUTPUT_INFORMATION_START_SELECTOR: Final[str] = "001"
OUTPUT_INFORMATION_MAX_SELECTOR: Final[int] = 999
OUTPUT_INFORMATION_MAX_PAGES: Final[int] = 200
OUTPUT_INFORMATION_MAX_ROWS_PER_PAGE: Final[int] = 20
OUTPUT_INFORMATION_FIXED_LENGTH: Final[int] = 14
OUTPUT_INFORMATION_NAME_MAX_LENGTH: Final[int] = 32
OUTPUT_INFORMATION_SUPERVISION_TIME_VALUES: Final[frozenset[str]] = frozenset(
    "-01234567"
)
OUTPUT_INFORMATION_FLAG_VALUES: Final[frozenset[str]] = frozenset("YN-")
OUTPUT_INFORMATION_BACKEND_RANGES: Final[tuple[range, ...]] = (
    range(450, 475),
    range(480, 500),
)
OUTPUT_INFORMATION_SUPERVISION_MINUTES: Final[dict[str, int]] = {
    "0": 0,
    "1": 3,
    "2": 60,
    "3": 240,
}


@dataclass(slots=True)
class OutputInformationRecord:
    """One parsed row from a lowercase `?Zi` reply."""

    selector: str
    backend_value: str
    supervision_time_code: str
    output_real_time_status: str
    trip_with_panel_bell: str
    name: str

    @property
    def number(self) -> int:
        """Return the numeric selector value."""
        return int(self.selector, 10)

    @property
    def backend_linked(self) -> bool:
        """Return True for the backend-linked selector shape."""
        return (
            self.backend_value != "--------"
            or any(
                self.number in selector_range
                for selector_range in OUTPUT_INFORMATION_BACKEND_RANGES
            )
        )

    @property
    def local_output(self) -> bool:
        """Return True for the ordinary local output-information row shape."""
        return not self.backend_linked

    @property
    def output_real_time_status_enabled(self) -> bool | None:
        """Return the confirmed local Output Real-Time Status flag."""
        if not self.local_output:
            return None
        if self.output_real_time_status == "Y":
            return True
        if self.output_real_time_status == "N":
            return False
        return None

    @property
    def backend_serial(self) -> str | None:
        """Return the backend serial/mapped value when present."""
        if self.backend_value == "--------":
            return None
        return self.backend_value

    @property
    def supervision_time_minutes(self) -> int | None:
        """Return the known supervision-time meaning for backend rows."""
        return OUTPUT_INFORMATION_SUPERVISION_MINUTES.get(self.supervision_time_code)

    @property
    def trip_with_panel_bell_enabled(self) -> bool | None:
        """Return the backend Trip With Panel/Bell flag when meaningful."""
        if not self.backend_linked:
            return None
        if self.trip_with_panel_bell == "Y":
            return True
        if self.trip_with_panel_bell == "N":
            return False
        return None


@dataclass(slots=True)
class OutputInformationPage:
    """One parsed lowercase `?Zi` reply page."""

    records: list[OutputInformationRecord]
    has_terminal_marker: bool
    raw_reply: bytes


@dataclass(slots=True)
class OutputInformationReply:
    """Parsed result of a complete lowercase `?Zi` output-information query."""

    records: list[OutputInformationRecord]
    complete: bool
    raw_replies: list[bytes]

    @property
    def outputs(self) -> list[OutputInformationRecord]:
        """Return ordinary local output-information rows."""
        return [record for record in self.records if record.local_output]

    @property
    def backend_records(self) -> list[OutputInformationRecord]:
        """Return backend-linked rows."""
        return [record for record in self.records if record.backend_linked]


class TransactionQueryOutputInformation(Transaction):
    """Complete paged lowercase `?Zi` Output Information query."""

    __slots__ = ("max_pages", "start_selector")

    def __init__(
        self,
        start_selector: int | str = OUTPUT_INFORMATION_START_SELECTOR,
        *,
        max_pages: int = OUTPUT_INFORMATION_MAX_PAGES,
    ) -> None:
        selector = normalize_output_information_selector(start_selector)
        if max_pages < 1:
            raise ValueError(f"max_pages must be >= 1, got: {max_pages!r}")
        super().__init__(
            body=f"?Zi{selector}",
            completion=payload_required(),
            label="query_output_information",
        )
        self.start_selector = selector
        self.max_pages = int(max_pages)

    async def execute_in_session(
        self,
        exchange: TransactionRunner,
        *,
        session_mode,
        endpoint: PanelEndpoint | None = None,
    ) -> Transaction:
        del endpoint

        selector = self.start_selector
        records: list[OutputInformationRecord] = []
        raw_replies: list[bytes] = []
        seen_start_selectors: set[str] = set()

        for _page_index in range(self.max_pages):
            if selector in seen_start_selectors:
                raise SessionProtocolError(
                    f"Output information query selector walk repeated at {selector!r}"
                )
            seen_start_selectors.add(selector)

            exchange_result = await exchange(f"?Zi{selector}", self.completion)
            self.record_exchange(exchange_result, session_mode=session_mode)

            if exchange_result.response is None:
                raise SessionProtocolError(
                    "Output information query completed without a reply payload"
                )

            page = parse_output_information_page(exchange_result.response)
            raw_replies.append(page.raw_reply)
            records.extend(page.records)

            next_selector = _next_output_information_selector(page.records)
            if next_selector is None:
                self.parsed_response = OutputInformationReply(
                    records=records,
                    complete=True,
                    raw_replies=raw_replies,
                )
                return self

            if int(next_selector, 10) <= int(selector, 10):
                raise SessionProtocolError(
                    f"Output information query selector walk did not advance: {selector!r} -> {next_selector!r}"
                )
            selector = next_selector

        raise SessionProtocolError("Output information query exceeded max page count")


def normalize_output_information_selector(selector: int | str) -> str:
    """Normalize a lowercase `?Zi` selector to a three-digit value."""
    if isinstance(selector, int):
        if not 1 <= selector <= OUTPUT_INFORMATION_MAX_SELECTOR:
            raise ValueError(
                f"Output information selector must be 1..{OUTPUT_INFORMATION_MAX_SELECTOR}, got: {selector}"
            )
        return f"{selector:03d}"

    text = str(selector).strip()
    if text.startswith("?Zi"):
        text = text[3:]
    if not text:
        raise ValueError("Output information selector must not be empty")
    if not text.isdigit():
        raise ValueError(f"Malformed output information selector: {selector!r}")

    value = int(text, 10)
    if not 1 <= value <= OUTPUT_INFORMATION_MAX_SELECTOR:
        raise ValueError(
            f"Output information selector must be 1..{OUTPUT_INFORMATION_MAX_SELECTOR}, got: {selector!r}"
        )
    return f"{value:03d}"


def parse_output_information_page(reply: bytes) -> OutputInformationPage:
    """Parse one raw panel reply page for lowercase `?Zi`."""
    payload = _extract_output_information_payload(reply)
    cleaned = payload.rstrip(b"\r\x00")
    if cleaned == OUTPUT_INFORMATION_PAGE_TERMINATOR:
        return OutputInformationPage(records=[], has_terminal_marker=True, raw_reply=reply)
    if not cleaned:
        raise SessionProtocolError("Empty ?Zi reply payload")
    if not cleaned.endswith(
        OUTPUT_INFORMATION_RECORD_SEPARATOR + OUTPUT_INFORMATION_PAGE_TERMINATOR
    ):
        raise SessionProtocolError(f"Malformed ?Zi reply missing terminator: {reply!r}")

    parts = cleaned.split(OUTPUT_INFORMATION_RECORD_SEPARATOR)
    records: list[OutputInformationRecord] = []
    has_terminal_marker = False

    for part in parts:
        if not part:
            raise SessionProtocolError(f"Malformed ?Zi reply contained an empty record: {reply!r}")
        if has_terminal_marker:
            raise SessionProtocolError(
                f"Malformed ?Zi reply contained data after terminator: {reply!r}"
            )
        if part == OUTPUT_INFORMATION_PAGE_TERMINATOR:
            has_terminal_marker = True
            continue

        records.append(_parse_output_information_record(part))
        if len(records) > OUTPUT_INFORMATION_MAX_ROWS_PER_PAGE:
            raise SessionProtocolError(
                f"Malformed ?Zi reply exceeded {OUTPUT_INFORMATION_MAX_ROWS_PER_PAGE} rows: {reply!r}"
            )

    if not has_terminal_marker:
        raise SessionProtocolError(f"Malformed ?Zi reply missing terminator: {reply!r}")

    return OutputInformationPage(
        records=records,
        has_terminal_marker=has_terminal_marker,
        raw_reply=reply,
    )


def _parse_output_information_record(raw_record: bytes) -> OutputInformationRecord:
    """Parse one fixed-prefix lowercase `?Zi` row."""
    if len(raw_record) < OUTPUT_INFORMATION_FIXED_LENGTH:
        raise SessionProtocolError(f"Malformed ?Zi output-information record: {raw_record!r}")

    selector = _parse_output_information_selector_field(raw_record[0:3], raw_record)
    backend_value = _decode_output_information_ascii(
        raw_record[3:11],
        raw_record=raw_record,
        label="backend value",
    )
    if backend_value != "--------" and not backend_value.isdigit():
        raise SessionProtocolError(f"Malformed ?Zi backend value: {raw_record!r}")

    supervision_time_code = _decode_output_information_ascii(
        raw_record[11:12],
        raw_record=raw_record,
        label="supervision time code",
    )
    if supervision_time_code not in OUTPUT_INFORMATION_SUPERVISION_TIME_VALUES:
        raise SessionProtocolError(f"Malformed ?Zi supervision time code: {raw_record!r}")

    output_real_time_status = _decode_output_information_ascii(
        raw_record[12:13],
        raw_record=raw_record,
        label="output real-time status",
    )
    if output_real_time_status not in OUTPUT_INFORMATION_FLAG_VALUES:
        raise SessionProtocolError(f"Malformed ?Zi output real-time status: {raw_record!r}")

    trip_with_panel_bell = _decode_output_information_ascii(
        raw_record[13:14],
        raw_record=raw_record,
        label="trip with panel bell",
    )
    if trip_with_panel_bell not in OUTPUT_INFORMATION_FLAG_VALUES:
        raise SessionProtocolError(f"Malformed ?Zi trip-with-panel flag: {raw_record!r}")

    name = _decode_output_information_ascii(
        raw_record[OUTPUT_INFORMATION_FIXED_LENGTH:],
        raw_record=raw_record,
        label="name",
    ).rstrip()
    if len(name) > OUTPUT_INFORMATION_NAME_MAX_LENGTH:
        raise SessionProtocolError(
            f"Malformed ?Zi name exceeds {OUTPUT_INFORMATION_NAME_MAX_LENGTH} chars: {raw_record!r}"
        )

    return OutputInformationRecord(
        selector=selector,
        backend_value=backend_value,
        supervision_time_code=supervision_time_code,
        output_real_time_status=output_real_time_status,
        trip_with_panel_bell=trip_with_panel_bell,
        name=name,
    )


def _parse_output_information_selector_field(
    raw_value: bytes,
    raw_record: bytes,
) -> str:
    value = _decode_output_information_ascii(
        raw_value,
        raw_record=raw_record,
        label="selector",
    )
    if not value.isdigit():
        raise SessionProtocolError(f"Malformed ?Zi selector: {raw_record!r}")
    parsed = int(value, 10)
    if not 1 <= parsed <= OUTPUT_INFORMATION_MAX_SELECTOR:
        raise SessionProtocolError(f"?Zi selector out of range: {raw_record!r}")
    return f"{parsed:03d}"


def _extract_output_information_payload(reply: bytes) -> bytes:
    """Extract the body that follows the lowercase `*Zi`/`!Zi`/`?Zi` marker."""
    for marker in OUTPUT_INFORMATION_REPLY_PREFIXES:
        index = reply.find(marker)
        if index == -1:
            continue
        return reply[index + len(marker):]

    raise SessionProtocolError("Reply did not contain a Zi marker")


def _next_output_information_selector(
    records: list[OutputInformationRecord],
) -> str | None:
    """Return the next selector using highest-visible-row progression."""
    if not records:
        return None

    value = max(record.number for record in records) + 1
    if value <= OUTPUT_INFORMATION_MAX_SELECTOR:
        return f"{value:03d}"
    return None


def _decode_output_information_ascii(
    raw_value: bytes,
    *,
    raw_record: bytes,
    label: str,
) -> str:
    try:
        return raw_value.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise SessionProtocolError(f"Malformed ?Zi {label}: {raw_record!r}") from exc
