"""Stateless `?ZL` zone-settings transaction and reply parsing.

`?ZL` reads one direct zone-settings row, while lowercase `?Zl` behaves more
like a list page. The parser supports both because they share the same record
layout.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import SessionProtocolError
from .models import Transaction, payload_required
from .zone_control import normalize_zone_number

ZONE_SETTINGS_RECORD_SEPARATOR = b"\x1e"
ZONE_SETTINGS_REPLY_PREFIXES = (b"*ZL", b"!ZL", b"?ZL", b"*Zl", b"!Zl", b"?Zl")
ZONE_SETTINGS_FIXED_LENGTH = 98
ZONE_SETTINGS_LEGACY_FIXED_LENGTH = 83
ZONE_SETTINGS_LAYOUT_CURRENT_98 = "current_98"
ZONE_SETTINGS_LAYOUT_LEGACY_83 = "legacy_83"
ZONE_SETTINGS_TERMINATOR = b"---"
ZONE_SETTINGS_NAME_MAX_LENGTH = 32
ZONE_SETTINGS_FLAG_VALUES = frozenset("YN")
ZONE_SETTINGS_FLAG54_VALUES = frozenset("FN")
ZONE_SETTINGS_PIR_PULSE_VALUES = frozenset("24")
ZONE_SETTINGS_PIR_SENSITIVITY_VALUES = frozenset("LH")
ZONE_SETTINGS_ENTRY_DELAY_VALUES = frozenset("1234")
ZONE_SETTINGS_NAME_PREFIX_FLAGS = frozenset("YN")
ZONE_SETTINGS_ALPHANUMERIC_TYPE_CODES = frozenset({"A1", "A2"})


@dataclass(slots=True)
class ZoneSettingsRecord:
    """One decoded zone-settings row from a `?ZL` or `?Zl` reply.

    Known fields are exposed with product-facing names from the firmware-backed
    `?ZL` map. Compatibility aliases preserve the older offset-style names.
    """

    number: str
    type_code: str
    area: str
    swinger_bypass: str
    keypad_bitmask: str
    retard: str
    fire_panel_slave: str
    priority: str
    arming_zone_special_word: str
    dmp_wireless: str
    report_with_account_area: str
    disarmed_open_action: str
    disarmed_open_output: str
    disarmed_open_output_mode: str
    disarmed_short_action: str
    disarmed_short_output: str
    disarmed_short_output_mode: str
    armed_open_action: str
    armed_open_output: str
    armed_open_output_mode: str
    armed_short_action: str
    armed_short_output: str
    armed_short_output_mode: str
    entry_delay_number: str
    fast_response: str
    fixed_literal_34: str
    cross_zone: str
    supervision_time_code: str
    transmitter_contact_high_bit: str
    disarm_disable: str
    normally_open: str
    transmitter_serial: str
    transmitter_contact_index: str
    supervision_time_index: str
    led_operation: str
    normally_open_duplicate: str
    disarm_disable_duplicate: str
    pir_pulse_count: str
    pir_sensitivity: str
    zone_real_time_status: str
    filler_4a_4c: str
    follow_area: str
    zone_audit_days: str
    traffic_count: str
    chime: str | None
    wireless_pir_pet_immunity: str | None
    lockdown: str | None
    internal_type5_slot: str | None
    compatible_wireless: str | None
    expander_serial: str | None
    name: str
    name_prefix: str = ""
    layout: str = ZONE_SETTINGS_LAYOUT_CURRENT_98

    @property
    def unused(self) -> bool:
        """Return True for rows that are not active monitored zone definitions."""
        return self.unconfigured or self.type_code == "UN" or self.name == "* UNUSED *"

    @property
    def unconfigured(self) -> bool:
        """Return True for the `--` type, which the panel does not monitor."""
        return self.type_code == "--"

    @property
    def monitored(self) -> bool:
        """Return True when the panel should consider this row a configured zone."""
        return not self.unused

    @property
    def flag_07(self) -> str:
        """Compatibility alias for `swinger_bypass`."""
        return self.swinger_bypass

    @property
    def nibble_word_08_0f(self) -> str:
        """Compatibility alias for the prewarn/presignal keypad bitmask."""
        return self.keypad_bitmask

    @property
    def flag_10(self) -> str:
        """Compatibility alias for `retard`."""
        return self.retard

    @property
    def flag_11(self) -> str:
        """Compatibility alias for `fire_panel_slave`."""
        return self.fire_panel_slave

    @property
    def flag_12(self) -> str:
        """Compatibility alias for `priority`."""
        return self.priority

    @property
    def special_word_13_1a(self) -> str:
        """Compatibility alias for `arming_zone_special_word`."""
        return self.arming_zone_special_word

    @property
    def marker_1b(self) -> str:
        """Compatibility alias for the formerly unnamed DMP wireless field."""
        return self.dmp_wireless

    @property
    def type_field_1c_1d(self) -> str:
        """Compatibility alias for `report_with_account_area`."""
        return self.report_with_account_area

    @property
    def flag_33(self) -> str:
        """Compatibility alias for `fast_response`."""
        return self.fast_response

    @property
    def literal_34(self) -> str:
        """Compatibility alias for `fixed_literal_34`."""
        return self.fixed_literal_34

    @property
    def flag_35(self) -> str:
        """Compatibility alias for `cross_zone`."""
        return self.cross_zone

    @property
    def display_option(self) -> str:
        """Compatibility alias for `supervision_time_code`."""
        return self.supervision_time_code

    @property
    def flag_37(self) -> str:
        """Compatibility alias for `transmitter_contact_high_bit`."""
        return self.transmitter_contact_high_bit

    @property
    def flag_38(self) -> str:
        """Compatibility alias for `disarm_disable`."""
        return self.disarm_disable

    @property
    def flag_39(self) -> str:
        """Compatibility alias for `normally_open`."""
        return self.normally_open

    @property
    def reference8(self) -> str:
        """Compatibility alias for the transmitter serial field."""
        return self.transmitter_serial

    @property
    def numeric_42(self) -> str:
        """Compatibility alias for `transmitter_contact_index`."""
        return self.transmitter_contact_index

    @property
    def numeric_43(self) -> str:
        """Compatibility alias for `supervision_time_index`."""
        return self.supervision_time_index

    @property
    def flag_44(self) -> str:
        """Compatibility alias for `led_operation`."""
        return self.led_operation

    @property
    def flag_45(self) -> str:
        """Compatibility alias for `normally_open_duplicate`."""
        return self.normally_open_duplicate

    @property
    def flag_46(self) -> str:
        """Compatibility alias for `disarm_disable_duplicate`."""
        return self.disarm_disable_duplicate

    @property
    def flag_49(self) -> str:
        """Compatibility alias for `zone_real_time_status`."""
        return self.zone_real_time_status

    @property
    def type_field_4d_4e(self) -> str:
        """Compatibility alias for `follow_area`."""
        return self.follow_area

    @property
    def type_field_4f_51(self) -> str:
        """Compatibility alias for `zone_audit_days`."""
        return self.zone_audit_days

    @property
    def flag_52(self) -> str:
        """Compatibility alias for `traffic_count`."""
        return self.traffic_count

    @property
    def numeric_53(self) -> str:
        """Compatibility alias for `chime`."""
        return self.chime

    @property
    def flag_54(self) -> str:
        """Compatibility alias for `wireless_pir_pet_immunity`."""
        return self.wireless_pir_pet_immunity

    @property
    def type5_flag_55(self) -> str:
        """Compatibility alias for `lockdown`."""
        return self.lockdown

    @property
    def slot_56(self) -> str:
        """Compatibility alias for `internal_type5_slot`."""
        return self.internal_type5_slot

    @property
    def reference_mode_57(self) -> str:
        """Compatibility alias for `compatible_wireless`."""
        return self.compatible_wireless

    @property
    def reference10(self) -> str:
        """Compatibility alias for the expander serial field."""
        return self.expander_serial


@dataclass(slots=True)
class ZoneSettingsPage:
    """One parsed `?ZL`/`?Zl` reply page."""

    records: list[ZoneSettingsRecord]
    has_terminal_marker: bool
    raw_reply: bytes

    @property
    def short_default(self) -> bool:
        """Return True for the observed bare short form `*ZL---` / `*Zl---`."""
        return self.has_terminal_marker and not self.records


@dataclass(slots=True)
class ZoneSettingsReply:
    """Parsed result of one single-zone `?ZLNNN` transaction."""

    requested_zone: str
    zone: ZoneSettingsRecord | None
    records: list[ZoneSettingsRecord]
    has_terminal_marker: bool
    raw_reply: bytes

    @property
    def found(self) -> bool:
        """Return True when the requested zone was present in the reply."""
        return self.zone is not None

    @property
    def short_default(self) -> bool:
        """Return True for the observed bare short form `*ZL---` / `*Zl---`."""
        return self.has_terminal_marker and not self.records


class TransactionQueryZoneSettings(Transaction):
    """Query settings for one zone with a single `?ZLNNN` request."""

    __slots__ = ("zone_number",)

    def __init__(self, zone: int | str) -> None:
        zone_number = normalize_zone_settings_number(zone)
        self.zone_number = zone_number
        super().__init__(body=f"?ZL{zone_number}", completion=payload_required(), label="query_zone_settings", parser=lambda reply: parse_zone_settings_reply(reply, requested_zone=zone_number))


def normalize_zone_settings_number(zone: int | str) -> str:
    """Normalize a `?ZL`/`?Zl` selector to a 3-digit zone number."""
    if isinstance(zone, int):
        return normalize_zone_number(zone)

    text = str(zone).strip()
    if text.startswith("?ZL") or text.startswith("?Zl"):
        text = text[3:]
    return normalize_zone_number(text)


def parse_zone_settings_reply(
    reply: bytes,
    *,
    requested_zone: int | str,
) -> ZoneSettingsReply:
    """Parse one raw panel reply and select the requested `?ZLNNN` zone."""
    requested = normalize_zone_settings_number(requested_zone)
    page = parse_zone_settings_page(reply)
    matches = [record for record in page.records if record.number == requested]
    if len(matches) > 1:
        raise SessionProtocolError(f"?ZL reply contained duplicate zone {requested}")

    return ZoneSettingsReply(requested_zone=requested, zone=matches[0] if matches else None, records=page.records, has_terminal_marker=page.has_terminal_marker, raw_reply=page.raw_reply)


def parse_zone_settings_page(reply: bytes) -> ZoneSettingsPage:
    """Parse one raw panel reply page for the `?ZL`/`?Zl` family.

    Direct uppercase reads often contain one record with no terminal marker.
    Lowercase list pages can contain one or more records followed by `---`.
    """
    payload = _extract_zone_settings_payload(reply)
    cleaned = payload.rstrip(b"\r\x00")
    if cleaned == ZONE_SETTINGS_TERMINATOR:
        return ZoneSettingsPage(records=[], has_terminal_marker=True, raw_reply=reply)
    if not cleaned:
        raise SessionProtocolError("Empty ?ZL reply payload")

    parts = cleaned.split(ZONE_SETTINGS_RECORD_SEPARATOR)
    trailing_empty_count = 0
    for part in reversed(parts):
        if part != b"":
            break
        trailing_empty_count += 1
    if trailing_empty_count:
        last_non_empty_index = len(parts) - trailing_empty_count - 1
        if last_non_empty_index >= 0 and parts[last_non_empty_index] == ZONE_SETTINGS_TERMINATOR:
            raise SessionProtocolError(
                f"Malformed ?ZL reply contained a separator after terminator: {reply!r}"
            )
        parts = parts[:-trailing_empty_count]

    records: list[ZoneSettingsRecord] = []
    has_terminal_marker = False

    for part in parts:
        if not part:
            raise SessionProtocolError(f"Malformed ?ZL reply contained an empty record: {reply!r}")
        if has_terminal_marker:
            raise SessionProtocolError(
                f"Malformed ?ZL reply contained data after terminator: {reply!r}"
            )
        if part == ZONE_SETTINGS_TERMINATOR:
            has_terminal_marker = True
            continue

        records.append(_parse_zone_settings_record(part))

    return ZoneSettingsPage(records=records, has_terminal_marker=has_terminal_marker, raw_reply=reply)


def _parse_zone_settings_record(raw_record: bytes) -> ZoneSettingsRecord:
    """Parse one fixed-body `?ZL`/`?Zl` row."""
    if len(raw_record) >= ZONE_SETTINGS_FIXED_LENGTH:
        fixed_length = ZONE_SETTINGS_FIXED_LENGTH
        layout = ZONE_SETTINGS_LAYOUT_CURRENT_98
    elif len(raw_record) >= ZONE_SETTINGS_LEGACY_FIXED_LENGTH:
        fixed_length = ZONE_SETTINGS_LEGACY_FIXED_LENGTH
        layout = ZONE_SETTINGS_LAYOUT_LEGACY_83
    else:
        raise SessionProtocolError(f"Malformed ?ZL zone-settings record: {raw_record!r}")

    fixed = raw_record[:fixed_length]
    name_prefix, name = _split_zone_settings_name_tail(
        raw_record,
        fixed_length=fixed_length,
    )
    number_value = _parse_decimal_field(
        fixed[0:3],
        raw_record=raw_record,
        label="zone number",
        minimum=1,
        maximum=999,
    )
    area_value = _parse_decimal_field(
        fixed[5:7],
        raw_record=raw_record,
        label="zone area",
        minimum=0,
        maximum=32,
    )
    disarmed_open_action, disarmed_open_output, disarmed_open_output_mode = (
        _parse_action_group_fields(
            fixed[30:35],
            raw_record=raw_record,
            label="disarmed open",
        )
    )
    disarmed_short_action, disarmed_short_output, disarmed_short_output_mode = (
        _parse_action_group_fields(
            fixed[35:40],
            raw_record=raw_record,
            label="disarmed short",
        )
    )
    armed_open_action, armed_open_output, armed_open_output_mode = _parse_action_group_fields(
        fixed[40:45],
        raw_record=raw_record,
        label="armed open",
    )
    armed_short_action, armed_short_output, armed_short_output_mode = _parse_action_group_fields(
        fixed[45:50],
        raw_record=raw_record,
        label="armed short",
    )
    chime: str | None = None
    wireless_pir_pet_immunity: str | None = None
    lockdown: str | None = None
    internal_type5_slot: str | None = None
    compatible_wireless: str | None = None
    expander_serial: str | None = None

    if layout == ZONE_SETTINGS_LAYOUT_CURRENT_98:
        chime = _parse_digit_in_range(
            fixed[83:84],
            raw_record=raw_record,
            label="chime",
            minimum=0,
            maximum=3,
        )
        wireless_pir_pet_immunity = _decode_enum(
            fixed[84:85],
            raw_record=raw_record,
            label="wireless PIR pet immunity",
            values=ZONE_SETTINGS_FLAG54_VALUES,
        )
        lockdown = _decode_ascii(
            fixed[85:86],
            raw_record=raw_record,
            label="lockdown",
        )
        internal_type5_slot = _decode_ascii(
            fixed[86:87],
            raw_record=raw_record,
            label="internal type-5 slot",
        )
        compatible_wireless = _parse_flag(
            fixed[87:88],
            raw_record=raw_record,
            label="compatible wireless",
        )
        expander_serial = _decode_ascii(
            fixed[88:98],
            raw_record=raw_record,
            label="expander serial",
        )

    return ZoneSettingsRecord(
        number=f"{number_value:03d}",
        type_code=_parse_zone_type(fixed[3:5], raw_record=raw_record),
        area=f"{area_value:02d}",
        swinger_bypass=_parse_flag(fixed[7:8], raw_record=raw_record, label="swinger bypass"),
        keypad_bitmask=_parse_hex_text(
            fixed[8:16],
            raw_record=raw_record,
            label="keypad bitmask",
        ),
        retard=_parse_flag(fixed[16:17], raw_record=raw_record, label="retard"),
        fire_panel_slave=_parse_flag(
            fixed[17:18],
            raw_record=raw_record,
            label="fire panel slave",
        ),
        priority=_parse_flag(fixed[18:19], raw_record=raw_record, label="priority"),
        arming_zone_special_word=_decode_ascii(
            fixed[19:27],
            raw_record=raw_record,
            label="arming-zone special word",
        ),
        dmp_wireless=_decode_ascii(
            fixed[27:28],
            raw_record=raw_record,
            label="DMP wireless flag",
        ),
        report_with_account_area=_parse_digit_text(
            fixed[28:30],
            raw_record=raw_record,
            label="report with account area",
        ),
        disarmed_open_action=disarmed_open_action,
        disarmed_open_output=disarmed_open_output,
        disarmed_open_output_mode=disarmed_open_output_mode,
        disarmed_short_action=disarmed_short_action,
        disarmed_short_output=disarmed_short_output,
        disarmed_short_output_mode=disarmed_short_output_mode,
        armed_open_action=armed_open_action,
        armed_open_output=armed_open_output,
        armed_open_output_mode=armed_open_output_mode,
        armed_short_action=armed_short_action,
        armed_short_output=armed_short_output,
        armed_short_output_mode=armed_short_output_mode,
        entry_delay_number=_decode_enum(
            fixed[50:51],
            raw_record=raw_record,
            label="entry delay number",
            values=ZONE_SETTINGS_ENTRY_DELAY_VALUES,
        ),
        fast_response=_parse_flag(fixed[51:52], raw_record=raw_record, label="fast response"),
        fixed_literal_34=_decode_ascii(fixed[52:53], raw_record=raw_record, label="literal 0x34"),
        cross_zone=_parse_flag(fixed[53:54], raw_record=raw_record, label="cross zone"),
        supervision_time_code=_parse_supervision_time_code(
            fixed[54:55],
            raw_record=raw_record,
        ),
        transmitter_contact_high_bit=_parse_flag(
            fixed[55:56],
            raw_record=raw_record,
            label="transmitter contact high bit",
        ),
        disarm_disable=_parse_flag(
            fixed[56:57],
            raw_record=raw_record,
            label="disarm disable",
        ),
        normally_open=_parse_flag(fixed[57:58], raw_record=raw_record, label="normally open"),
        transmitter_serial=_decode_ascii(
            fixed[58:66],
            raw_record=raw_record,
            label="transmitter serial",
        ),
        transmitter_contact_index=_parse_digit_in_range(
            fixed[66:67],
            raw_record=raw_record,
            label="transmitter contact index",
            minimum=0,
            maximum=3,
        ),
        supervision_time_index=_parse_digit_in_range(
            fixed[67:68],
            raw_record=raw_record,
            label="supervision time index",
            minimum=0,
            maximum=7,
        ),
        led_operation=_parse_flag(fixed[68:69], raw_record=raw_record, label="LED operation"),
        normally_open_duplicate=_parse_flag(
            fixed[69:70],
            raw_record=raw_record,
            label="normally open duplicate",
        ),
        disarm_disable_duplicate=_parse_flag(
            fixed[70:71],
            raw_record=raw_record,
            label="disarm disable duplicate",
        ),
        pir_pulse_count=_decode_enum(
            fixed[71:72],
            raw_record=raw_record,
            label="PIR pulse count",
            values=ZONE_SETTINGS_PIR_PULSE_VALUES,
        ),
        pir_sensitivity=_decode_enum(
            fixed[72:73],
            raw_record=raw_record,
            label="PIR sensitivity",
            values=ZONE_SETTINGS_PIR_SENSITIVITY_VALUES,
        ),
        zone_real_time_status=_parse_flag(
            fixed[73:74],
            raw_record=raw_record,
            label="zone real-time status",
        ),
        filler_4a_4c=_decode_ascii(fixed[74:77], raw_record=raw_record, label="filler 0x4a..0x4c"),
        follow_area=_parse_digit_text(
            fixed[77:79],
            raw_record=raw_record,
            label="follow area",
        ),
        zone_audit_days=_parse_zone_audit_days(
            fixed[79:82],
            raw_record=raw_record,
        ),
        traffic_count=_parse_flag(fixed[82:83], raw_record=raw_record, label="traffic count"),
        chime=chime,
        wireless_pir_pet_immunity=wireless_pir_pet_immunity,
        lockdown=lockdown,
        internal_type5_slot=internal_type5_slot,
        compatible_wireless=compatible_wireless,
        expander_serial=expander_serial,
        name=name,
        name_prefix=name_prefix,
        layout=layout,
    )


def _parse_action_group_fields(
    raw_value: bytes,
    *,
    raw_record: bytes,
    label: str,
) -> tuple[str, str, str]:
    """Split one 5-character action cell into action, output, and mode."""
    text = _decode_ascii(raw_value, raw_record=raw_record, label=label)
    action = "none" if text[0] == "-" else text[0]
    output = "none" if text[1:4] == "000" else text[1:4]
    return action, output, text[4]


def _parse_zone_type(raw_value: bytes, *, raw_record: bytes) -> str:
    type_code = _decode_ascii(raw_value, raw_record=raw_record, label="zone type")
    if len(type_code) != 2:
        raise SessionProtocolError(f"Malformed ?ZL zone type: {raw_record!r}")
    if type_code == "--" or type_code in ZONE_SETTINGS_ALPHANUMERIC_TYPE_CODES:
        return type_code
    if not type_code.isalpha() or not type_code.isupper():
        raise SessionProtocolError(f"Malformed ?ZL zone type: {raw_record!r}")
    return type_code


def _parse_flag(raw_value: bytes, *, raw_record: bytes, label: str) -> str:
    return _decode_enum(
        raw_value,
        raw_record=raw_record,
        label=label,
        values=ZONE_SETTINGS_FLAG_VALUES,
    )


def _parse_supervision_time_code(raw_value: bytes, *, raw_record: bytes) -> str:
    supervision_time_code = _decode_ascii(
        raw_value,
        raw_record=raw_record,
        label="supervision time code",
    )
    if len(supervision_time_code) != 1 or (
        not supervision_time_code.isalnum() and supervision_time_code != "-"
    ):
        raise SessionProtocolError(f"Malformed ?ZL supervision time code: {raw_record!r}")
    return supervision_time_code


def _parse_hex_text(raw_value: bytes, *, raw_record: bytes, label: str) -> str:
    value = _decode_ascii(raw_value, raw_record=raw_record, label=label)
    if any(character not in "0123456789ABCDEF" for character in value):
        raise SessionProtocolError(f"Malformed ?ZL {label}: {raw_record!r}")
    return value


def _parse_digit_text(
    raw_value: bytes,
    *,
    raw_record: bytes,
    label: str,
) -> str:
    value = _decode_ascii(raw_value, raw_record=raw_record, label=label)
    if not value.isdigit():
        raise SessionProtocolError(f"Malformed ?ZL {label}: {raw_record!r}")
    return value


def _parse_zone_audit_days(raw_value: bytes, *, raw_record: bytes) -> str:
    value = _parse_digit_text(raw_value, raw_record=raw_record, label="zone audit days")
    if int(value, 10) > 365:
        raise SessionProtocolError(f"Malformed ?ZL zone audit days: {raw_record!r}")
    return value


def _parse_digit_in_range(
    raw_value: bytes,
    *,
    raw_record: bytes,
    label: str,
    minimum: int,
    maximum: int,
) -> str:
    value = _parse_digit_text(raw_value, raw_record=raw_record, label=label)
    parsed = int(value, 10)
    if not minimum <= parsed <= maximum:
        raise SessionProtocolError(f"?ZL {label} out of range: {raw_record!r}")
    return value


def _parse_decimal_field(
    raw_value: bytes,
    *,
    raw_record: bytes,
    label: str,
    minimum: int,
    maximum: int,
) -> int:
    value = _parse_digit_text(raw_value, raw_record=raw_record, label=label)
    parsed = int(value, 10)
    if not minimum <= parsed <= maximum:
        raise SessionProtocolError(f"?ZL {label} out of range: {raw_record!r}")
    return parsed


def _decode_enum(
    raw_value: bytes,
    *,
    raw_record: bytes,
    label: str,
    values: frozenset[str],
) -> str:
    value = _decode_ascii(raw_value, raw_record=raw_record, label=label)
    if value not in values:
        raise SessionProtocolError(f"Malformed ?ZL {label}: {raw_record!r}")
    return value


def _decode_zone_settings_name(raw_name: bytes, *, raw_record: bytes) -> str:
    name = _decode_ascii(raw_name, raw_record=raw_record, label="zone name")
    if len(name) > ZONE_SETTINGS_NAME_MAX_LENGTH:
        raise SessionProtocolError(f"?ZL zone name too long: {raw_record!r}")
    return name


def _split_zone_settings_name_tail(
    raw_record: bytes,
    *,
    fixed_length: int,
) -> tuple[str, str]:
    """Split the fixed body from the visible zone name tail.

    Most records place the name directly at offset 98. A later live capture
    also showed a two-byte `-N` prefix before the visible name on one direct
    uppercase row. Preserve that prefix separately and return the cleaned
    visible name.
    """
    raw_name = raw_record[fixed_length:]
    if len(raw_name) >= 2:
        prefix = raw_name[:2]
        first = prefix[:1]
        second = prefix[1:2]
        try:
            prefix_text = prefix.decode("ascii")
        except UnicodeDecodeError:
            prefix_text = ""
        if (
            first == b"-"
            and second.decode("ascii", errors="ignore") in ZONE_SETTINGS_NAME_PREFIX_FLAGS
            and raw_name[2:]
        ):
            return prefix_text, _decode_zone_settings_name(raw_name[2:], raw_record=raw_record)

    return "", _decode_zone_settings_name(raw_name, raw_record=raw_record)


def _decode_ascii(raw_value: bytes, *, raw_record: bytes, label: str) -> str:
    try:
        value = raw_value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise SessionProtocolError(f"Malformed ?ZL {label}: {raw_record!r}") from exc

    if any(ord(character) < 0x20 or ord(character) > 0x7E for character in value):
        raise SessionProtocolError(f"Malformed ?ZL {label}: {raw_record!r}")
    return value


def _extract_zone_settings_payload(reply: bytes) -> bytes:
    """Extract the body that follows the `*ZL`/`*Zl` family marker."""
    for marker in ZONE_SETTINGS_REPLY_PREFIXES:
        index = reply.find(marker)
        if index == -1:
            continue
        return reply[index + len(marker) :]

    if b"-ZL" in reply or b"-Zl" in reply or b"-Z" in reply:
        raise SessionProtocolError(f"Panel denied ?ZL request: {reply!r}")

    raise SessionProtocolError("Reply did not contain a ZL marker")
