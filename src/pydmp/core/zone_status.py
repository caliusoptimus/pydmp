"""Stateless `?WB` transactions and reply parsing.

`?WB` is the zone snapshot query. In practice it is not a simple one-call
query: we discover areas first, then walk each area-scoped `?WB` iterator to
completion.
"""

from __future__ import annotations

from dataclasses import dataclass

from .area_status import AREA_QUERY_INITIAL_BODY, AreaStatusRecord, collect_area_status
from .errors import SessionProtocolError
from .models import CompletionPolicy, Transaction, TransactionRunner, payload_required

ZONE_RECORD_SEPARATOR = b"\x1e"
ZONE_REPLY_PREFIXES = (b"*WB", b"!WB", b"?WB")
ZONE_QUERY_CONTINUATION_BODY = "?WB"
ZONE_GLOBAL_AREA_NUMBER = "00"
ZONE_WILDCARD_AREA_SELECTOR = "**"
ZONE_START_ZONE = "001"
ZONE_EMIT_FLAG = "Y"
ZONE_QUERY_WILDCARD_BODY = f"?WB{ZONE_WILDCARD_AREA_SELECTOR}{ZONE_EMIT_FLAG}{ZONE_START_ZONE}"
ZONE_QUERY_MAX_PAGES = 256
ZONE_NAME_MAX_LENGTH = 32
ZONE_STATUS_CHARS = frozenset("NLOMSX")
ZONE_AREA_STATUS_CHARS = frozenset("ADS")
ZONE_AREA_EMIT_FLAG = "N"


@dataclass(slots=True)
class ZoneStatusRecord:
    """One parsed zone record from a `?WB` transaction."""

    number: str
    area_number: str
    status: str
    name: str


@dataclass(slots=True)
class ZoneStatusPage:
    """One parsed `?WB` reply page."""

    zones: list[ZoneStatusRecord]
    complete: bool
    raw_reply: bytes
    next_area_number: str


@dataclass(slots=True)
class ZoneStatusReply:
    """Parsed result of a complete `?WB` zone snapshot transaction."""

    zones: list[ZoneStatusRecord]
    areas: list[AreaStatusRecord]
    complete: bool
    raw_replies: list[bytes]


class TransactionQueryZones(Transaction):
    """Complete full-panel zone snapshot transaction.

    This transaction discovers areas through `?WA` first, then unions complete
    area-scoped `?WB` sweeps for those areas.
    """

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__(
            body=AREA_QUERY_INITIAL_BODY,
            completion=payload_required(),
            label="query_zones",
        )

    async def execute_in_session(
        self,
        exchange: TransactionRunner,
        *,
        session_mode,
        endpoint=None,
    ) -> Transaction:
        del endpoint
        # Delegate area discovery to the same full-panel ?WA loop used by
        # TransactionQueryAreas so this transaction cannot drift from it.
        discovered = await collect_area_status(self, exchange, session_mode=session_mode)

        raw_replies = list(discovered.raw_replies)
        zones_by_number: dict[str, ZoneStatusRecord] = {}
        zones_complete = True

        if discovered.areas:
            # Each area gets its own seeded `?WBxxY001` walk. Project captures
            # show that some zones only appear under their own area seed.
            for area in discovered.areas:
                sweep = await collect_zone_status_for_area(
                    self,
                    exchange,
                    area_number=area.number,
                    session_mode=session_mode,
                )
                raw_replies.extend(sweep.raw_replies)
                zones_complete = zones_complete and sweep.complete
                for zone in sweep.zones:
                    if zone.number in zones_by_number:
                        del zones_by_number[zone.number]
                    zones_by_number[zone.number] = zone
        else:
            # Area discovery should normally find at least area 01. If it does
            # not, wildcard is the least-assumptive fallback for global rows.
            sweep = await collect_zone_status_pages(
                self,
                exchange,
                initial_body=ZONE_QUERY_WILDCARD_BODY,
                session_mode=session_mode,
            )
            raw_replies.extend(sweep.raw_replies)
            zones_complete = sweep.complete
            for zone in sweep.zones:
                if zone.number in zones_by_number:
                    del zones_by_number[zone.number]
                zones_by_number[zone.number] = zone

        self.parsed_response = ZoneStatusReply(zones=sorted(zones_by_number.values(), key=lambda zone: int(zone.number)), areas=discovered.areas, complete=discovered.complete and zones_complete, raw_replies=raw_replies)
        return self


class TransactionQueryAllAreasAndZones(TransactionQueryZones):
    """Explicit alias for the full-panel `TransactionQueryZones` snapshot."""

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__()
        self.label = "query_all_areas_and_zones"


class TransactionQuerySpecificZones(Transaction):
    """One seeded `?WB` zone-status page.

    This is the narrow zone-status transaction: it sends one `?WB` request for
    a specific area selector and optional start selector, then parses only that
    reply page. It does not send bare `?WB` continuations.

    `end_zone` is an inclusive client-side result filter for rows present on
    that one returned page; the panel protocol does not expose a known
    wire-level end selector. The `?WB` flag is selected automatically: area
    `00` and wildcard `**` use `Y`, while areas `01`-`32` use `N`.
    """

    __slots__ = (
        "area_number",
        "start_zone",
        "end_zone",
        "query_flag",
        "include_global_zones",
    )

    def __init__(
        self,
        area_number: int | str | None = ZONE_WILDCARD_AREA_SELECTOR,
        *,
        start_zone: int | str = ZONE_START_ZONE,
        end_zone: int | str | None = None,
        include_global_zones: bool | None = None,
    ) -> None:
        del include_global_zones
        self.area_number = normalize_zone_query_area(area_number)
        self.start_zone = normalize_zone_query_selector(start_zone, label="start zone")
        self.end_zone = (
            None
            if end_zone is None
            else normalize_zone_query_selector(end_zone, label="end zone")
        )
        validate_zone_query_range(start_zone=self.start_zone, end_zone=self.end_zone)
        self.query_flag = _select_specific_zone_query_flag(self.area_number)
        self.include_global_zones = self.query_flag == ZONE_EMIT_FLAG
        super().__init__(
            body=_build_zone_query_body(
                area_number=self.area_number,
                start_zone=self.start_zone,
                include_global_zones=self.include_global_zones,
            ),
            completion=payload_required(),
            label="query_specific_zones",
        )

    async def execute_in_session(
        self,
        exchange: TransactionRunner,
        *,
        session_mode,
        endpoint=None,
    ) -> Transaction:
        del endpoint
        exchange_result = await exchange(self.body, self.completion)
        self.record_exchange(exchange_result, session_mode=session_mode)

        if exchange_result.response is None:
            raise SessionProtocolError(
                "Specific zone query completed without a reply payload"
            )

        initial_area_number = (
            ZONE_GLOBAL_AREA_NUMBER
            if self.area_number == ZONE_WILDCARD_AREA_SELECTOR
            else self.area_number
        )
        page = parse_zone_status_page(
            exchange_result.response,
            current_area_number=initial_area_number,
        )
        zones = _filter_zone_status_range(
            page.zones,
            start_zone=self.start_zone,
            end_zone=self.end_zone,
        )
        self.parsed_response = ZoneStatusReply(
            zones=sorted(zones, key=lambda zone: int(zone.number)),
            areas=[],
            complete=page.complete,
            raw_replies=[page.raw_reply],
        )
        return self


@dataclass(slots=True)
class ZoneStatusCollection:
    """Internal result for one full paged `?WB` sweep."""

    zones: list[ZoneStatusRecord]
    raw_replies: list[bytes]
    complete: bool


async def collect_zone_status_for_area(
    transaction: Transaction,
    exchange: TransactionRunner,
    *,
    area_number: str,
    start_zone: int | str = ZONE_START_ZONE,
    end_zone: int | str | None = None,
    include_global_zones: bool = True,
    session_mode,
) -> ZoneStatusCollection:
    """Collect a full paged `?WB` sweep for one discovered area."""
    normalized_area = normalize_zone_query_area(area_number)
    normalized_start = normalize_zone_query_selector(start_zone, label="start zone")
    normalized_end = (
        None
        if end_zone is None
        else normalize_zone_query_selector(end_zone, label="end zone")
    )
    validate_zone_query_range(start_zone=normalized_start, end_zone=normalized_end)
    collection = await collect_zone_status_pages(
        transaction,
        exchange,
        initial_body=_build_zone_query_body(
            area_number=normalized_area,
            start_zone=normalized_start,
            include_global_zones=include_global_zones,
        ),
        session_mode=session_mode,
    )
    if normalized_start == ZONE_START_ZONE and normalized_end is None:
        return collection
    return ZoneStatusCollection(
        zones=_filter_zone_status_range(
            collection.zones,
            start_zone=normalized_start,
            end_zone=normalized_end,
        ),
        raw_replies=collection.raw_replies,
        complete=collection.complete,
    )


async def collect_zone_status_pages(
    transaction: Transaction,
    exchange: TransactionRunner,
    *,
    initial_body: bytes | str,
    session_mode,
) -> ZoneStatusCollection:
    """Collect one seeded `?WB` iterator with bare continuations."""
    current_body = initial_body
    current_area_number = ZONE_GLOBAL_AREA_NUMBER
    collected_zones: list[ZoneStatusRecord] = []
    raw_replies: list[bytes] = []
    completion: CompletionPolicy = transaction.completion
    seen_pages: set[bytes] = set()

    for _page_number in range(ZONE_QUERY_MAX_PAGES):
        exchange_result = await exchange(current_body, completion)
        transaction.record_exchange(exchange_result, session_mode=session_mode)

        if exchange_result.response is None:
            raise SessionProtocolError("Zone query completed without a reply payload")

        page = parse_zone_status_page(exchange_result.response, current_area_number=current_area_number)
        page_signature = _zone_payload_signature(exchange_result.response)
        if page_signature in seen_pages:
            return ZoneStatusCollection(zones=collected_zones, raw_replies=raw_replies, complete=False)
        seen_pages.add(page_signature)

        raw_replies.append(page.raw_reply)
        collected_zones.extend(page.zones)
        current_area_number = page.next_area_number

        if _is_empty_zone_terminal(page, page_signature):
            return ZoneStatusCollection(zones=collected_zones, raw_replies=raw_replies, complete=True)

        current_body = ZONE_QUERY_CONTINUATION_BODY

    raise SessionProtocolError(
        f"Zone query exceeded {ZONE_QUERY_MAX_PAGES} pages without a terminator"
    )


def parse_zone_status_page(
    reply: bytes,
    *,
    current_area_number: str = ZONE_GLOBAL_AREA_NUMBER,
) -> ZoneStatusPage:
    """Parse one raw panel reply page for the `?WB` family.

    `?WB` pages can mix two row types:

    - `A...` area anchors, which change the active area for later zone rows
    - `L...` zone rows, which inherit the current active area
    """
    payload = _extract_zone_payload(reply)
    cleaned = payload.rstrip(b"\r\x00")
    if cleaned == b"-":
        return ZoneStatusPage(zones=[], complete=True, raw_reply=reply, next_area_number=current_area_number)
    if not cleaned:
        raise SessionProtocolError("Empty ?WB reply payload")

    parts = cleaned.split(ZONE_RECORD_SEPARATOR)
    zones: list[ZoneStatusRecord] = []
    complete = False
    next_area_number = current_area_number

    for part in parts:
        if not part:
            raise SessionProtocolError(
                f"Malformed ?WB reply contained an empty record: {reply!r}"
            )
        if complete:
            raise SessionProtocolError(
                f"Malformed ?WB reply contained data after terminator: {reply!r}"
            )
        if part == b"-":
            complete = True
            continue

        marker = part[:1]
        if marker == b"A":
            next_area_number = _parse_area_anchor(part)
            continue
        if marker == b"L":
            zones.append(_parse_zone_row(part, area_number=next_area_number))
            continue

        raise SessionProtocolError(f"Malformed ?WB record: {part!r}")

    return ZoneStatusPage(
        zones=zones,
        complete=complete,
        raw_reply=reply,
        next_area_number=next_area_number,
    )


def normalize_zone_query_area(area_number: int | str | None) -> str:
    """Normalize a `?WB` area selector to `00`-`32` or wildcard `**`."""
    if area_number is None:
        return ZONE_WILDCARD_AREA_SELECTOR
    text = str(area_number).strip()
    if text == ZONE_WILDCARD_AREA_SELECTOR:
        return text
    if not text.isdigit():
        raise ValueError(f"Zone query area must be numeric or '**', got: {area_number!r}")
    value = int(text)
    if not 0 <= value <= 32:
        raise ValueError(f"Zone query area must be between 0 and 32, got: {value}")
    return f"{value:02d}"


def normalize_zone_query_selector(selector: int | str, *, label: str) -> str:
    """Normalize a `?WB` visible zone selector to three digits."""
    text = str(selector).strip()
    if not text.isdigit():
        raise ValueError(f"Zone query {label} must be numeric, got: {selector!r}")
    value = int(text)
    if not 1 <= value <= 999:
        raise ValueError(f"Zone query {label} must be between 1 and 999, got: {value}")
    return f"{value:03d}"


def validate_zone_query_range(*, start_zone: str, end_zone: str | None) -> None:
    """Validate one inclusive `?WB` client-side selector range."""
    if end_zone is not None and int(end_zone) < int(start_zone):
        raise ValueError(f"Zone query end zone must be >= start zone, got: {end_zone}")


def _build_zone_query_body(
    *,
    area_number: str,
    start_zone: str,
    include_global_zones: bool,
) -> str:
    emit_flag = ZONE_EMIT_FLAG if include_global_zones else ZONE_AREA_EMIT_FLAG
    return f"?WB{area_number}{emit_flag}{start_zone}"


def _select_specific_zone_query_flag(area_number: str) -> str:
    if area_number in {ZONE_GLOBAL_AREA_NUMBER, ZONE_WILDCARD_AREA_SELECTOR}:
        return ZONE_EMIT_FLAG
    return ZONE_AREA_EMIT_FLAG


def _filter_zone_status_range(
    zones: list[ZoneStatusRecord],
    *,
    start_zone: str,
    end_zone: str | None,
) -> list[ZoneStatusRecord]:
    start = int(start_zone)
    end = None if end_zone is None else int(end_zone)
    return [
        zone
        for zone in zones
        if int(zone.number) >= start and (end is None or int(zone.number) <= end)
    ]


def _parse_area_anchor(raw_row: bytes) -> str:
    """Parse one `AxxxSNAME` area anchor row and return the active area."""
    if len(raw_row) < 5:
        raise SessionProtocolError(f"Malformed ?WB area anchor: {raw_row!r}")
    area_number = _parse_decimal_field(
        raw_row[1:4],
        raw_row=raw_row,
        label="area number",
        minimum=1,
        maximum=32,
    )
    state = _decode_ascii_field(raw_row[4:5], raw_row=raw_row, label="area state")
    if state not in ZONE_AREA_STATUS_CHARS:
        raise SessionProtocolError(f"Unexpected ?WB area state character: {raw_row!r}")
    _decode_status_name(raw_row[5:], raw_row=raw_row, label="area name")
    return f"{area_number:02d}"


def _parse_zone_row(raw_row: bytes, *, area_number: str) -> ZoneStatusRecord:
    """Parse one `LxxxSNAME` zone row."""
    if len(raw_row) < 5:
        raise SessionProtocolError(f"Malformed ?WB zone row: {raw_row!r}")
    zone_number = _parse_decimal_field(
        raw_row[1:4],
        raw_row=raw_row,
        label="zone number",
        minimum=1,
        maximum=999,
    )
    number = f"{zone_number:03d}"
    status = _decode_ascii_field(raw_row[4:5], raw_row=raw_row, label="zone status")
    if status not in ZONE_STATUS_CHARS:
        raise SessionProtocolError(f"Unexpected ?WB zone status character: {raw_row!r}")
    name = _decode_status_name(raw_row[5:], raw_row=raw_row, label="zone name")
    return ZoneStatusRecord(number=number, area_number=area_number, status=status, name=name)


def _parse_decimal_field(
    raw_value: bytes,
    *,
    raw_row: bytes,
    label: str,
    minimum: int,
    maximum: int,
) -> int:
    value = _decode_ascii_field(raw_value, raw_row=raw_row, label=label)
    if not value.isdigit():
        raise SessionProtocolError(f"Malformed ?WB {label}: {raw_row!r}")
    parsed = int(value)
    if not minimum <= parsed <= maximum:
        raise SessionProtocolError(f"?WB {label} out of range: {raw_row!r}")
    return parsed


def _decode_status_name(raw_name: bytes, *, raw_row: bytes, label: str) -> str:
    """Decode one visible area or zone name from a `?WB` row."""
    name = _decode_ascii_field(raw_name, raw_row=raw_row, label=label).strip()
    if not name:
        raise SessionProtocolError(f"Malformed ?WB record missing {label}: {raw_row!r}")
    if len(name) > ZONE_NAME_MAX_LENGTH:
        raise SessionProtocolError(
            f"Malformed ?WB {label} exceeds {ZONE_NAME_MAX_LENGTH} chars: {raw_row!r}"
        )
    return name


def _decode_ascii_field(raw_value: bytes, *, raw_row: bytes, label: str) -> str:
    """Decode one ASCII field and reject non-printable characters."""
    try:
        decoded = raw_value.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise SessionProtocolError(f"Malformed ?WB {label}: {raw_row!r}") from exc

    if any(ord(char) < 0x20 or ord(char) > 0x7E for char in decoded):
        raise SessionProtocolError(f"Malformed ?WB {label}: {raw_row!r}")
    return decoded


def _extract_zone_payload(reply: bytes) -> bytes:
    """Extract the body that follows the `*WB`/`!WB`/`?WB` marker."""
    for marker in ZONE_REPLY_PREFIXES:
        index = reply.find(marker)
        if index == -1:
            continue
        return reply[index + len(marker):]

    if b"-WB" in reply or b"-W" in reply:
        raise SessionProtocolError(f"Panel denied ?WB request: {reply!r}")

    raise SessionProtocolError("Reply did not contain a WB marker")


def _zone_payload_signature(reply: bytes) -> bytes:
    return _extract_zone_payload(reply).rstrip(b"\r\x00")


def _is_empty_zone_terminal(page: ZoneStatusPage, page_signature: bytes) -> bool:
    """Return `True` only for the explicit empty terminal page `*WB-`."""
    return page.complete and not page.zones and page_signature == b"-"
