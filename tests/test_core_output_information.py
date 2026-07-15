"""Readable tests for lowercase `?Zi` output-information parsing."""

import pytest

from pydmp.core import (
    CorePanelClient,
    OutputInformationPage,
    OutputInformationRecord,
    OutputInformationReply,
    PanelEndpoint,
    SessionProtocolError,
    SessionProfileBlankV2,
    TransactionQueryOutputInformation,
    normalize_output_information_selector,
    parse_output_information_page,
)


class FakeTransport:
    """Tiny scripted transport used to keep these tests focused on `?Zi`."""

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


def test_transaction_query_output_information_shape():
    transaction = TransactionQueryOutputInformation()

    assert transaction.body == "?Zi001"
    assert transaction.label == "query_output_information"
    assert transaction.parser is None
    assert transaction.start_selector == "001"
    assert transaction.max_pages == 200

    explicit = TransactionQueryOutputInformation("?Zi580", max_pages=3)
    assert explicit.body == "?Zi580"
    assert explicit.start_selector == "580"
    assert explicit.max_pages == 3

    assert normalize_output_information_selector(1) == "001"
    assert normalize_output_information_selector("7") == "007"
    assert normalize_output_information_selector("?Zi450") == "450"

    with pytest.raises(ValueError):
        normalize_output_information_selector(0)
    with pytest.raises(ValueError):
        normalize_output_information_selector("D01")
    with pytest.raises(ValueError):
        normalize_output_information_selector("?ZI001")
    with pytest.raises(ValueError):
        TransactionQueryOutputInformation(max_pages=0)


def test_parse_output_information_page_handles_live_local_rows():
    reply = (
        b"\x02@ 12345*Zi001---------N-OP1\x1e002---------Y-OP2"
        b"\x1e580---------Y-OPE580\x1e----\r\x00"
    )

    page = parse_output_information_page(reply)

    assert page == OutputInformationPage(
        records=[
            OutputInformationRecord(
                selector="001",
                backend_value="--------",
                supervision_time_code="-",
                output_real_time_status="N",
                trip_with_panel_bell="-",
                name="OP1",
            ),
            OutputInformationRecord(
                selector="002",
                backend_value="--------",
                supervision_time_code="-",
                output_real_time_status="Y",
                trip_with_panel_bell="-",
                name="OP2",
            ),
            OutputInformationRecord(
                selector="580",
                backend_value="--------",
                supervision_time_code="-",
                output_real_time_status="Y",
                trip_with_panel_bell="-",
                name="OPE580",
            ),
        ],
        has_terminal_marker=True,
        raw_reply=reply,
    )
    assert [record.selector for record in page.records] == ["001", "002", "580"]
    assert page.records[0].local_output is True
    assert page.records[0].backend_linked is False
    assert page.records[0].output_real_time_status_enabled is False
    assert page.records[0].backend_serial is None
    assert page.records[0].trip_with_panel_bell_enabled is None
    assert page.records[1].output_real_time_status_enabled is True


def test_parse_output_information_page_handles_backend_rows():
    reply = b"\x02@ 12345*Zi450152000001-YBACKEND\x1e----\r\x00"

    page = parse_output_information_page(reply)
    record = page.records[0]

    assert record.selector == "450"
    assert record.backend_linked is True
    assert record.local_output is False
    assert record.backend_serial == "15200000"
    assert record.supervision_time_code == "1"
    assert record.supervision_time_minutes == 3
    assert record.output_real_time_status == "-"
    assert record.output_real_time_status_enabled is None
    assert record.trip_with_panel_bell == "Y"
    assert record.trip_with_panel_bell_enabled is True
    assert record.name == "BACKEND"


def test_parse_output_information_page_handles_empty_terminal_page():
    reply = b"\x02@ 12345*Zi----\r\x00"

    assert parse_output_information_page(reply) == OutputInformationPage(
        records=[],
        has_terminal_marker=True,
        raw_reply=reply,
    )


@pytest.mark.parametrize(
    "reply",
    [
        b"\x02@ 12345*Zi\r\x00",
        b"\x02@ 12345*Zi001---------Y-OP1\r\x00",
        b"\x02@ 12345*Zi001---------Y-OP1\x1e\x1e----\r\x00",
        b"\x02@ 12345*Zi001---------Y-OP1\x1e----\x1e002---------Y-OP2\x1e----\r\x00",
        b"\x02@ 12345*Zi001\r\x00",
        b"\x02@ 12345*Zi001ABCDEFG-Y-OP1\x1e----\r\x00",
        b"\x02@ 12345*Zi001---------Q-OP1\x1e----\r\x00",
        b"\x02@ 12345*Zi000---------Y-OP1\x1e----\r\x00",
        (
            b"\x02@ 12345*Zi001---------Y-OP1\x1e002---------Y-OP2\x1e003---------Y-OP3"
            b"\x1e004---------Y-OP4\x1e005---------Y-OP5\x1e006---------Y-OP6"
            b"\x1e007---------Y-OP7\x1e008---------Y-OP8\x1e009---------Y-OP9"
            b"\x1e010---------Y-OP10\x1e011---------Y-OP11\x1e012---------Y-OP12"
            b"\x1e013---------Y-OP13\x1e014---------Y-OP14\x1e015---------Y-OP15"
            b"\x1e016---------Y-OP16\x1e017---------Y-OP17\x1e018---------Y-OP18"
            b"\x1e019---------Y-OP19\x1e020---------Y-OP20\x1e021---------Y-OP21"
            b"\x1e----\r\x00"
        ),
    ],
)
def test_parse_output_information_page_rejects_malformed_reply(reply):
    with pytest.raises(SessionProtocolError):
        parse_output_information_page(reply)


@pytest.mark.asyncio
async def test_core_panel_client_query_output_information_walks_explicit_pages():
    factory, transports = make_transport_factory(
        scripted_replies=[
            b"\x02@ 12345+V02012345\r",
            (
                b"\x02@ 12345*Zi001---------Y-OP1\x1e002---------Y-OP2"
                b"\x1e580---------Y-OPE580\x1e----\r\x00"
            ),
            b"\x02@ 12345*Zi----\r\x00",
            b"\x02@ 12345+V\r",
        ]
    )
    client = CorePanelClient(
        PanelEndpoint(host="panel", account="12345", idle_disconnect_seconds=0.01),
        session_profile=SessionProfileBlankV2(),
        transport_factory=factory,
    )

    try:
        reply = await client.query_output_information()
        assert isinstance(reply, OutputInformationReply)
        assert reply.complete is True
        assert [record.selector for record in reply.records] == ["001", "002", "580"]
        assert [record.selector for record in reply.outputs] == ["001", "002", "580"]
        assert reply.backend_records == []
        assert len(reply.raw_replies) == 2
        assert transports[0].requests[0] == b"@12345!V2                \r"
        assert transports[0].requests[1:3] == [
            b"@12345?Zi001\r",
            b"@12345?Zi581\r",
        ]
    finally:
        await client.close()
