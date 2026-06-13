"""Stateless `?Zo` system-options transaction and reply parsing.

`?Zo` returns one packed global System Options record. The layout here is based
on live panel probes, the project notes, and the complete 2.13 firmware image.
Most fields are confirmed from keypad changes; `dual_eol` is firmware-derived
from the keypad prompt string and the matching ADC threshold path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .errors import SessionProtocolError
from .models import Transaction, payload_required

SYSTEM_OPTIONS_REPLY_PREFIXES: Final[tuple[bytes, ...]] = (b"*Zo", b"!Zo", b"?Zo")
SYSTEM_OPTIONS_BODY_LENGTH: Final[int] = 76
SYSTEM_OPTIONS_YN_VALUES: Final[frozenset[str]] = frozenset({"Y", "N"})
SYSTEM_OPTIONS_HEX_ALPHABET: Final[bytes] = b"0123456789ABCDEF"
SYSTEM_OPTIONS_DEFAULT_OBFUSCATION_SOURCE_TEXT: Final[str] = " " * 16
SYSTEM_OPTIONS_OBSCURED_PASSPHRASE_HEX_LENGTH: Final[int] = 8

SYSTEM_ARMING_TYPES: Final[dict[str, str]] = {
    "N": "area_independent",
    "A": "all_perimeter",
    "H": "home_sleep_away",
    "G": "home_sleep_away_guest",
}
PROGRAMMING_LANGUAGE_TYPES: Final[dict[str, str]] = {
    "1": "english",
    "2": "spanish",
    "3": "french",
    "4": "czech_tentative",
}
SECONDARY_LANGUAGE_TYPES: Final[dict[str, str]] = {
    "0": "none",
    "1": "english",
    "2": "spanish",
    "3": "french",
}
TBL_AUDIBLE_TYPES: Final[dict[str, str]] = {
    "0": "any",
    "1": "day",
    "2": "min",
}
KEYPAD_ARMED_LED_TYPES: Final[dict[str, str]] = {
    "0": "all",
    "1": "any",
}
WIRELESS_ENCRYPTION_TYPES: Final[dict[str, str]] = {
    "N": "none",
    "A": "all",
    "B": "both",
}
EOL_VALUE_TYPES: Final[dict[str, str]] = {
    "1": "1k_eol",
    "2": "2k2_eol",
    "3": "unknown_3",
    "4": "unknown_4",
}


@dataclass(slots=True)
class SystemOptionsReply:
    """Decoded `?Zo` System Options record."""

    closing_wait: bool
    entry_delay_1: int
    entry_delay_2: int
    entry_delay_3: int
    entry_delay_4: int
    cross_zone_time: int
    retard_delay: int
    send_16_char_names: bool
    swinger_bypass_trips: int
    reset_swinger_bypass: bool
    time_change: bool
    hours_from_gmt: int
    latch_supervisory_zones: bool
    power_fail_hours: int
    programming_primary_language_code: str
    programming_primary_language: str
    programming_secondary_language_code: str
    programming_secondary_language: str
    user_primary_language_code: str
    user_primary_language: str
    user_secondary_language_code: str
    user_secondary_language: str
    legacy_optional_32: str
    bypass_limit: int
    wireless_house_code: int
    detect_wireless_jamming: bool
    keypad_panic_keys: bool
    system_arming_type_code: str
    system_arming_type: str
    occupied_premise: bool
    tbl_audible_code: str
    tbl_audible: str
    enhanced_zone_test: bool
    instant_arming: bool
    dual_eol: bool
    keypad_armed_led_code: str
    keypad_armed_led: str
    use_false_alarm_question: bool
    allow_own_user_code_change: bool
    panic_supervision: bool
    gap_49_51: str
    weather_zip_raw: str
    weather_zip: str | None
    zone_activity_hours: int
    wireless_encryption_code: str
    wireless_encryption: str
    obscured_passphrase: str
    wireless_passphrase_hex: str | None
    wireless_passphrase: str | None
    gap_67_73: str
    eol_value_code: str
    eol_value: str
    thermostat_unit_celsius: bool
    extra_tail: str
    raw_body: bytes
    raw_reply: bytes


class TransactionQuerySystemOptions(Transaction):
    """Query panel System Options with a single `?Zo` request."""

    def __init__(self) -> None:
        super().__init__(
            body="?Zo",
            completion=payload_required(),
            label="query_system_options",
            parser=parse_system_options_reply,
        )


def parse_system_options_reply(reply: bytes) -> SystemOptionsReply:
    """Parse one raw panel reply for the `?Zo` System Options family."""
    payload = _extract_system_options_payload(reply)
    cleaned = payload.rstrip(b"\r\x00")
    if len(cleaned) < SYSTEM_OPTIONS_BODY_LENGTH:
        raise SessionProtocolError(
            f"Malformed ?Zo reply body shorter than {SYSTEM_OPTIONS_BODY_LENGTH} bytes: {reply!r}"
        )

    body = cleaned[:SYSTEM_OPTIONS_BODY_LENGTH]
    extra_tail = _decode_printable_ascii(
        cleaned[SYSTEM_OPTIONS_BODY_LENGTH:],
        raw_body=cleaned,
        label="extra tail",
    )
    text = _decode_printable_ascii(body, raw_body=body, label="body")

    system_arming_code = text[39]
    weather_zip_raw = text[52:57]
    wireless_encryption_code = text[58]
    obscured_passphrase = _parse_hex_text(
        text[59:67],
        raw_body=body,
        label="obscured passphrase",
    )
    wireless_passphrase_hex = _deobscure_passphrase_hex(
        obscured_passphrase,
        account_number=_extract_system_options_account(reply),
    )
    eol_value_code = text[74]

    return SystemOptionsReply(
        closing_wait=_parse_yn(text[0], raw_body=body, label="closing wait"),
        entry_delay_1=_parse_digits(text[1:4], raw_body=body, label="entry delay 1"),
        entry_delay_2=_parse_digits(text[4:7], raw_body=body, label="entry delay 2"),
        entry_delay_3=_parse_digits(text[7:10], raw_body=body, label="entry delay 3"),
        entry_delay_4=_parse_digits(text[10:13], raw_body=body, label="entry delay 4"),
        cross_zone_time=_parse_digits(text[13:16], raw_body=body, label="cross zone time"),
        retard_delay=_parse_digits(text[16:19], raw_body=body, label="retard delay"),
        send_16_char_names=_parse_yn(text[19], raw_body=body, label="send 16 char names"),
        swinger_bypass_trips=_parse_digits(
            text[20],
            raw_body=body,
            label="swinger bypass trips",
        ),
        reset_swinger_bypass=_parse_yn(
            text[21],
            raw_body=body,
            label="reset swinger bypass",
        ),
        time_change=_parse_yn(text[22], raw_body=body, label="time change"),
        hours_from_gmt=_parse_digits(text[23:25], raw_body=body, label="hours from GMT"),
        latch_supervisory_zones=_parse_yn(
            text[25],
            raw_body=body,
            label="latch supervisory zones",
        ),
        power_fail_hours=_parse_digits(text[26:28], raw_body=body, label="power fail hours"),
        programming_primary_language_code=text[28],
        programming_primary_language=_decode_known(
            text[28],
            PROGRAMMING_LANGUAGE_TYPES,
        ),
        programming_secondary_language_code=text[29],
        programming_secondary_language=_decode_known(
            text[29],
            SECONDARY_LANGUAGE_TYPES,
        ),
        user_primary_language_code=text[30],
        user_primary_language=_decode_known(text[30], PROGRAMMING_LANGUAGE_TYPES),
        user_secondary_language_code=text[31],
        user_secondary_language=_decode_known(text[31], SECONDARY_LANGUAGE_TYPES),
        legacy_optional_32=text[32],
        bypass_limit=_parse_digits(text[33], raw_body=body, label="bypass limit"),
        wireless_house_code=_parse_digits(
            text[34:37],
            raw_body=body,
            label="wireless house code",
        ),
        detect_wireless_jamming=_parse_yn(
            text[37],
            raw_body=body,
            label="detect wireless jamming",
        ),
        keypad_panic_keys=_parse_yn(text[38], raw_body=body, label="keypad panic keys"),
        system_arming_type_code=system_arming_code,
        system_arming_type=_decode_known(system_arming_code, SYSTEM_ARMING_TYPES),
        occupied_premise=_parse_yn(text[40], raw_body=body, label="occupied premise"),
        tbl_audible_code=text[41],
        tbl_audible=_decode_known(text[41], TBL_AUDIBLE_TYPES),
        enhanced_zone_test=_parse_yn(text[42], raw_body=body, label="enhanced zone test"),
        instant_arming=_parse_yn(text[43], raw_body=body, label="instant arming"),
        dual_eol=_parse_yn(text[44], raw_body=body, label="dual EOL"),
        keypad_armed_led_code=text[45],
        keypad_armed_led=_decode_known(text[45], KEYPAD_ARMED_LED_TYPES),
        use_false_alarm_question=_parse_yn(
            text[46],
            raw_body=body,
            label="use false alarm question",
        ),
        allow_own_user_code_change=_parse_yn(
            text[47],
            raw_body=body,
            label="allow own user code change",
        ),
        panic_supervision=_parse_yn(text[48], raw_body=body, label="panic supervision"),
        gap_49_51=text[49:52],
        weather_zip_raw=weather_zip_raw,
        weather_zip=_parse_weather_zip(weather_zip_raw, raw_body=body),
        zone_activity_hours=_parse_digits(text[57], raw_body=body, label="zone activity hours"),
        wireless_encryption_code=wireless_encryption_code,
        wireless_encryption=_decode_known(
            wireless_encryption_code,
            WIRELESS_ENCRYPTION_TYPES,
        ),
        obscured_passphrase=obscured_passphrase,
        wireless_passphrase_hex=wireless_passphrase_hex,
        wireless_passphrase=(
            _strip_leading_zero_bytes_hex(wireless_passphrase_hex)
            if wireless_passphrase_hex is not None
            else None
        ),
        gap_67_73=text[67:74],
        eol_value_code=eol_value_code,
        eol_value=_decode_known(eol_value_code, EOL_VALUE_TYPES),
        thermostat_unit_celsius=_parse_yn(
            text[75],
            raw_body=body,
            label="thermostat unit Celsius",
        ),
        extra_tail=extra_tail,
        raw_body=body,
        raw_reply=reply,
    )


def _parse_yn(raw_value: str, *, raw_body: bytes, label: str) -> bool:
    if raw_value not in SYSTEM_OPTIONS_YN_VALUES:
        raise SessionProtocolError(f"Unexpected ?Zo {label} value: {raw_body!r}")
    return raw_value == "Y"


def _parse_digits(raw_value: str, *, raw_body: bytes, label: str) -> int:
    if not raw_value.isdigit():
        raise SessionProtocolError(f"Malformed ?Zo {label}: {raw_body!r}")
    return int(raw_value, 10)


def _parse_hex_text(raw_value: str, *, raw_body: bytes, label: str) -> str:
    if len(raw_value) != SYSTEM_OPTIONS_OBSCURED_PASSPHRASE_HEX_LENGTH:
        raise SessionProtocolError(f"Malformed ?Zo {label}: {raw_body!r}")
    if any(char not in "0123456789ABCDEFabcdef" for char in raw_value):
        raise SessionProtocolError(f"Malformed ?Zo {label}: {raw_body!r}")
    return raw_value.upper()


def _extract_system_options_account(reply: bytes) -> str | None:
    """Return the visible account digits from a normal panel reply frame."""
    marker_index = min(
        (index for marker in SYSTEM_OPTIONS_REPLY_PREFIXES if (index := reply.find(marker)) != -1),
        default=-1,
    )
    if marker_index == -1:
        return None

    at_index = reply.rfind(b"@", 0, marker_index)
    if at_index == -1:
        return None

    account_text = reply[at_index + 1 : marker_index].decode("ascii", errors="ignore").strip()
    if not account_text.isdigit() or not 1 <= len(account_text) <= 5:
        return None
    return account_text


def _deobscure_passphrase_hex(
    visible_hex: str,
    *,
    account_number: str | None,
) -> str | None:
    if account_number is None:
        return None

    visible = bytes.fromhex(visible_hex)
    seed = _derive_passphrase_obfuscation_seed(account_number)
    stream = _passphrase_obfuscation_stream(seed, len(visible))
    clear = bytes(item ^ mask for item, mask in zip(visible, stream, strict=True))
    return clear.hex().upper()


def _derive_passphrase_obfuscation_seed(
    account_number: str,
    *,
    selector: int = 0,
    source_text: str = SYSTEM_OPTIONS_DEFAULT_OBFUSCATION_SOURCE_TEXT,
) -> int:
    source = source_text.encode("ascii", errors="replace").ljust(8, b" ")
    seed = (int(account_number) + selector) & 0xFF
    seed ^= _passphrase_obfuscation_pair_mix(source, 0, 1)
    seed ^= _passphrase_obfuscation_pair_mix(source, 6, 7)
    return seed


def _passphrase_obfuscation_pair_mix(
    source: bytes,
    first_index: int,
    second_index: int,
) -> int:
    high = _lookup_obfuscation_hex_digit(source[first_index])
    low = _lookup_obfuscation_hex_digit(source[second_index])
    return ((high << 4) + low) & 0xFF


def _lookup_obfuscation_hex_digit(value: int) -> int:
    try:
        return SYSTEM_OPTIONS_HEX_ALPHABET.index(value)
    except ValueError:
        return 0xFF


def _passphrase_obfuscation_stream(seed: int, length: int) -> bytes:
    stream: list[int] = []
    state = seed
    for _ in range(length):
        state = _advance_passphrase_obfuscation_stream_byte(state)
        stream.append(state)
    return bytes(stream)


def _advance_passphrase_obfuscation_stream_byte(state: int) -> int:
    feedback = ((state >> 3) ^ (state >> 2) ^ state ^ (state >> 4)) & 1
    next_state = ((state >> 1) | (feedback << 7)) & 0xFF
    if next_state == 0:
        next_state = 0xFF
    return next_state


def _strip_leading_zero_bytes_hex(value: str) -> str:
    stripped = value
    while len(stripped) > 2 and stripped.startswith("00"):
        stripped = stripped[2:]
    return stripped


def _parse_weather_zip(raw_value: str, *, raw_body: bytes) -> str | None:
    if raw_value == " " * 5:
        return None
    if not raw_value.isdigit():
        raise SessionProtocolError(f"Malformed ?Zo weather ZIP: {raw_body!r}")
    return raw_value


def _decode_known(raw_value: str, values: dict[str, str]) -> str:
    return values.get(raw_value, f"unknown_{raw_value}")


def _decode_printable_ascii(raw_value: bytes, *, raw_body: bytes, label: str) -> str:
    try:
        decoded = raw_value.decode("ascii", errors="strict")
    except UnicodeDecodeError as exc:
        raise SessionProtocolError(f"Malformed ?Zo {label}: {raw_body!r}") from exc

    if any(ord(char) < 0x20 or ord(char) > 0x7E for char in decoded):
        raise SessionProtocolError(f"Malformed ?Zo {label}: {raw_body!r}")
    return decoded


def _extract_system_options_payload(reply: bytes) -> bytes:
    """Extract the body that follows the `*Zo`/`!Zo`/`?Zo` marker."""
    for marker in SYSTEM_OPTIONS_REPLY_PREFIXES:
        index = reply.find(marker)
        if index == -1:
            continue
        return reply[index + len(marker) :]

    if b"-Zo" in reply or b"-Z" in reply:
        raise SessionProtocolError(f"Panel denied ?Zo request: {reply!r}")

    raise SessionProtocolError("Reply did not contain a Zo marker")
