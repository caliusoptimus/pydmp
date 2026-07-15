"""Readable tests for `?Zo` system-options parsing."""

import pytest

from pydmp.core import (
    CorePanelClient,
    PanelEndpoint,
    SessionProfileBlankV2,
    SessionProtocolError,
    SystemOptionsReply,
    TransactionQuerySystemOptions,
    parse_system_options_reply,
)


BASELINE_ZO_BODY = (
    b"N030060090120004010N2NY06Y011010-0000NYNY1NNN0YNN---     "
    b"0N197B56CD-------1N"
)
LEGACY_58_ZO_BODY = b"N030060090120004010Y2NY06Y011010-0000NYAY1NYN0YNN000     0"


class FakeTransport:
    """Tiny scripted transport used to keep these tests focused on system options."""

    def __init__(self, endpoint, scripted_replies=None):
        self.endpoint = endpoint
        self._scripted_replies = list(scripted_replies or [])
        self.is_connected = False
        self.requests = []

    async def connect(self):
        self.is_connected = True

    async def disconnect(self):
        self.is_connected = False

    async def exchange(self, request: bytes, completion):
        del completion
        self.requests.append(request)
        if self._scripted_replies:
            return self._scripted_replies.pop(0)
        return b""


def make_transport_factory(scripted_replies=None):
    """Return a transport factory plus the created fake transports."""
    transports = []

    def factory(endpoint):
        transport = FakeTransport(endpoint, scripted_replies=scripted_replies)
        transports.append(transport)
        return transport

    return factory, transports


def test_transaction_query_system_options_shape():
    transaction = TransactionQuerySystemOptions()

    assert transaction.body == "?Zo"
    assert transaction.label == "query_system_options"
    assert transaction.parser is parse_system_options_reply


def test_parse_system_options_reply_decodes_known_213_layout():
    reply = b"\x02@ 12345*Zo" + BASELINE_ZO_BODY + b"\r\x00"

    parsed = parse_system_options_reply(reply)

    assert isinstance(parsed, SystemOptionsReply)
    assert parsed.layout == "current_76"
    assert parsed.raw_reply == reply
    assert parsed.raw_body == BASELINE_ZO_BODY
    assert parsed.extra_tail == ""
    assert parsed.closing_wait is False
    assert parsed.entry_delay_1 == 30
    assert parsed.entry_delay_2 == 60
    assert parsed.entry_delay_3 == 90
    assert parsed.entry_delay_4 == 120
    assert parsed.cross_zone_time == 4
    assert parsed.retard_delay == 10
    assert parsed.send_16_char_names is False
    assert parsed.swinger_bypass_trips == 2
    assert parsed.reset_swinger_bypass is False
    assert parsed.time_change is True
    assert parsed.hours_from_gmt == 6
    assert parsed.latch_supervisory_zones is True
    assert parsed.power_fail_hours == 1
    assert parsed.programming_primary_language_code == "1"
    assert parsed.programming_primary_language == "english"
    assert parsed.programming_secondary_language_code == "0"
    assert parsed.programming_secondary_language == "none"
    assert parsed.user_primary_language_code == "1"
    assert parsed.user_primary_language == "english"
    assert parsed.user_secondary_language_code == "0"
    assert parsed.user_secondary_language == "none"
    assert parsed.legacy_optional_32 == "-"
    assert parsed.bypass_limit == 0
    assert parsed.wireless_house_code == 0
    assert parsed.detect_wireless_jamming is False
    assert parsed.keypad_panic_keys is True
    assert parsed.system_arming_type_code == "N"
    assert parsed.system_arming_type == "area_independent"
    assert parsed.occupied_premise is True
    assert parsed.tbl_audible_code == "1"
    assert parsed.tbl_audible == "day"
    assert parsed.enhanced_zone_test is False
    assert parsed.instant_arming is False
    assert parsed.dual_eol is False
    assert parsed.keypad_armed_led_code == "0"
    assert parsed.keypad_armed_led == "all"
    assert parsed.use_false_alarm_question is True
    assert parsed.allow_own_user_code_change is False
    assert parsed.panic_supervision is False
    assert parsed.gap_49_51 == "---"
    assert parsed.weather_zip_raw == "     "
    assert parsed.weather_zip is None
    assert parsed.zone_activity_hours == 0
    assert parsed.wireless_encryption_code == "N"
    assert parsed.wireless_encryption == "none"
    assert parsed.obscured_passphrase == "197B56CD"
    assert parsed.wireless_passphrase_hex == "85B531FE"
    assert parsed.wireless_passphrase == "85B531FE"
    assert parsed.gap_67_73 == "-------"
    assert parsed.eol_value_code == "1"
    assert parsed.eol_value == "1k_eol"
    assert parsed.thermostat_unit_celsius is False


def test_parse_system_options_reply_decodes_legacy_58_layout():
    reply = b"\x02@ 12345*Zo" + LEGACY_58_ZO_BODY + b"\r\x00"

    parsed = parse_system_options_reply(reply)

    assert parsed.layout == "legacy_58"
    assert parsed.raw_reply == reply
    assert parsed.raw_body == LEGACY_58_ZO_BODY
    assert parsed.extra_tail == ""
    assert parsed.closing_wait is False
    assert parsed.entry_delay_1 == 30
    assert parsed.entry_delay_2 == 60
    assert parsed.entry_delay_3 == 90
    assert parsed.entry_delay_4 == 120
    assert parsed.cross_zone_time == 4
    assert parsed.retard_delay == 10
    assert parsed.send_16_char_names is True
    assert parsed.swinger_bypass_trips == 2
    assert parsed.reset_swinger_bypass is False
    assert parsed.time_change is True
    assert parsed.hours_from_gmt == 6
    assert parsed.latch_supervisory_zones is True
    assert parsed.power_fail_hours == 1
    assert parsed.system_arming_type_code == "A"
    assert parsed.system_arming_type == "all_perimeter"
    assert parsed.occupied_premise is True
    assert parsed.tbl_audible == "day"
    assert parsed.instant_arming is True
    assert parsed.dual_eol is False
    assert parsed.keypad_armed_led == "all"
    assert parsed.use_false_alarm_question is True
    assert parsed.allow_own_user_code_change is False
    assert parsed.panic_supervision is False
    assert parsed.gap_49_51 == "000"
    assert parsed.weather_zip is None
    assert parsed.zone_activity_hours == 0
    assert parsed.wireless_encryption_code is None
    assert parsed.wireless_encryption is None
    assert parsed.obscured_passphrase is None
    assert parsed.wireless_passphrase_hex is None
    assert parsed.wireless_passphrase is None
    assert parsed.gap_67_73 is None
    assert parsed.eol_value_code is None
    assert parsed.eol_value is None
    assert parsed.thermostat_unit_celsius is None


def test_parse_system_options_reply_decodes_recently_confirmed_fields():
    body = bytearray(BASELINE_ZO_BODY)
    body[39] = ord("A")
    body[41] = ord("2")
    body[44] = ord("Y")
    body[45] = ord("1")
    body[52:57] = b"95621"
    body[58] = ord("B")
    body[59:67] = b"9CDF7622"
    body[74] = ord("2")
    body[75] = ord("Y")

    parsed = parse_system_options_reply(b"\x02@ 12345*Zo" + bytes(body) + b"\r")

    assert parsed.system_arming_type == "all_perimeter"
    assert parsed.tbl_audible == "min"
    assert parsed.dual_eol is True
    assert parsed.keypad_armed_led == "any"
    assert parsed.weather_zip == "95621"
    assert parsed.wireless_encryption == "both"
    assert parsed.obscured_passphrase == "9CDF7622"
    assert parsed.wireless_passphrase_hex == "00111111"
    assert parsed.wireless_passphrase == "111111"
    assert parsed.eol_value == "2k2_eol"
    assert parsed.thermostat_unit_celsius is True


def test_parse_system_options_reply_leaves_passphrase_empty_without_account():
    parsed = parse_system_options_reply(b"*Zo" + BASELINE_ZO_BODY + b"\r\x00")

    assert parsed.obscured_passphrase == "197B56CD"
    assert parsed.wireless_passphrase_hex is None
    assert parsed.wireless_passphrase is None


def test_parse_system_options_reply_preserves_future_tail_and_unknown_codes():
    body = bytearray(BASELINE_ZO_BODY)
    body[28] = ord("9")
    body[39] = ord("Z")

    parsed = parse_system_options_reply(b"\x02@ 12345*Zo" + bytes(body) + b"XY\r\x00")

    assert parsed.layout == "current_76"
    assert parsed.programming_primary_language == "unknown_9"
    assert parsed.system_arming_type == "unknown_Z"
    assert parsed.extra_tail == "XY"


@pytest.mark.parametrize(
    "reply",
    [
        b"\x02@ 12345*WA" + BASELINE_ZO_BODY + b"\r",
        b"\x02@ 12345*Zo\r\x00",
        b"\x02@ 12345*Zo" + BASELINE_ZO_BODY[:75] + b"\r\x00",
        b"\x02@ 12345*Zo" + LEGACY_58_ZO_BODY + b"X\r\x00",
        b"\x02@ 12345*Zo" + BASELINE_ZO_BODY[:1] + b"X" + BASELINE_ZO_BODY[2:] + b"\r",
        b"\x02@ 12345*Zo" + BASELINE_ZO_BODY[:59] + b"NOT_HEX!" + BASELINE_ZO_BODY[67:] + b"\r",
        b"\x02@ 12345*Zo" + BASELINE_ZO_BODY[:52] + b"95 21" + BASELINE_ZO_BODY[57:] + b"\r",
    ],
)
def test_parse_system_options_reply_rejects_malformed_payloads(reply):
    with pytest.raises(SessionProtocolError):
        parse_system_options_reply(reply)


@pytest.mark.asyncio
async def test_core_panel_client_query_system_options_sends_single_zo_request():
    reply = b"\x02@ 12345*Zo" + BASELINE_ZO_BODY + b"\r\x00"
    factory, transports = make_transport_factory(
        scripted_replies=[
            b"\x02@ 12345+V02012345\r",
            reply,
            b"\x02@ 12345+V\r",
        ]
    )
    client = CorePanelClient(
        PanelEndpoint(host="panel", account="12345", idle_disconnect_seconds=0.01),
        session_profile=SessionProfileBlankV2(),
        transport_factory=factory,
    )

    try:
        parsed = await client.query_system_options()
        assert parsed.system_arming_type == "area_independent"
        assert transports[0].requests[0] == b"@12345!V2                \r"
        assert transports[0].requests[1:2] == [b"@12345?Zo\r"]
    finally:
        await client.close()
