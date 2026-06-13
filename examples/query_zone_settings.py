"""Query one zone-settings record with a direct transaction example."""

from __future__ import annotations

import argparse

from _example_support import (
    add_common_command_arguments,
    build_manager_from_args,
    format_bytes_for_cli,
    normalize_name_for_display,
    print_transaction_wire_data,
    run_async_entrypoint,
)
from pydmp.core import TransactionQueryZoneSettings, ZoneSettingsReply


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for this example."""
    parser = argparse.ArgumentParser(description="Query one zone-settings record with the new stateless core.")
    add_common_command_arguments(parser)
    parser.add_argument("--zone", required=True, help="Zone number to query, from 1 to 999.")
    return parser


async def async_main() -> int:
    """Run the example."""
    args = build_parser().parse_args()
    manager = build_manager_from_args(args)

    try:
        transaction = await manager.submit(TransactionQueryZoneSettings(args.zone))
        reply = transaction.parsed_response
        if not isinstance(reply, ZoneSettingsReply):
            raise ValueError("Zone-settings transaction completed without a parsed reply")

        print(f"requested zone: {reply.requested_zone}")
        print(f"found: {reply.found}")
        print(f"short_default: {reply.short_default}")
        print(f"records_on_page: {len(reply.records)}")
        print(f"has_terminal_marker: {reply.has_terminal_marker}")
        print(f"raw_response: {format_bytes_for_cli(reply.raw_reply)}")

        if reply.zone is None:
            print("The requested zone was not present in the reply.")
        else:
            zone = reply.zone
            print(f"number: {zone.number}")
            print(f"type_code: {zone.type_code}")
            print(f"area: {zone.area}")
            print(f"swinger_bypass: {zone.swinger_bypass}")
            print(f"keypad_bitmask: {zone.keypad_bitmask}")
            print(f"retard: {zone.retard}")
            print(f"fire_panel_slave: {zone.fire_panel_slave}")
            print(f"priority: {zone.priority}")
            print(f"arming_zone_special_word: {zone.arming_zone_special_word}")
            print(f"dmp_wireless: {zone.dmp_wireless}")
            print(f"report_with_account_area: {zone.report_with_account_area}")
            print(f"entry_delay_number: {zone.entry_delay_number}")
            print(f"fast_response: {zone.fast_response}")
            print(f"fixed_literal_34: {zone.fixed_literal_34}")
            print(f"cross_zone: {zone.cross_zone}")
            print(f"supervision_time_code: {zone.supervision_time_code}")
            print(f"transmitter_contact_high_bit: {zone.transmitter_contact_high_bit}")
            print(f"disarm_disable: {zone.disarm_disable}")
            print(f"normally_open: {zone.normally_open}")
            print(f"transmitter_serial: {zone.transmitter_serial}")
            print(f"transmitter_contact_index: {zone.transmitter_contact_index}")
            print(f"supervision_time_index: {zone.supervision_time_index}")
            print(f"led_operation: {zone.led_operation}")
            print(f"normally_open_duplicate: {zone.normally_open_duplicate}")
            print(f"disarm_disable_duplicate: {zone.disarm_disable_duplicate}")
            print(f"pir_pulse_count: {zone.pir_pulse_count}")
            print(f"pir_sensitivity: {zone.pir_sensitivity}")
            print(f"zone_real_time_status: {zone.zone_real_time_status}")
            print(f"filler_4a_4c: {zone.filler_4a_4c}")
            print(f"follow_area: {zone.follow_area}")
            print(f"zone_audit_days: {zone.zone_audit_days}")
            print(f"traffic_count: {zone.traffic_count}")
            print(f"chime: {zone.chime}")
            print(f"wireless_pir_pet_immunity: {zone.wireless_pir_pet_immunity}")
            print(f"lockdown: {zone.lockdown}")
            print(f"internal_type5_slot: {zone.internal_type5_slot}")
            print(f"compatible_wireless: {zone.compatible_wireless}")
            print(f"expander_serial: {zone.expander_serial}")
            print(f"disarmed_open_action: {zone.disarmed_open_action}")
            print(f"disarmed_open_output: {zone.disarmed_open_output}")
            print(f"disarmed_open_output_mode: {zone.disarmed_open_output_mode}")
            print(f"disarmed_short_action: {zone.disarmed_short_action}")
            print(f"disarmed_short_output: {zone.disarmed_short_output}")
            print(f"disarmed_short_output_mode: {zone.disarmed_short_output_mode}")
            print(f"armed_open_action: {zone.armed_open_action}")
            print(f"armed_open_output: {zone.armed_open_output}")
            print(f"armed_open_output_mode: {zone.armed_open_output_mode}")
            print(f"armed_short_action: {zone.armed_short_action}")
            print(f"armed_short_output: {zone.armed_short_output}")
            print(f"armed_short_output_mode: {zone.armed_short_output_mode}")
            print(f"name_prefix: {zone.name_prefix or '<none>'}")
            print(f"name: {normalize_name_for_display(zone.name)}")

        if args.show_raw:
            print_transaction_wire_data(transaction.wire_requests, transaction.wire_responses)
    finally:
        await manager.close()

    return 0


def main() -> int:
    """Synchronous entrypoint used by `python3 query_zone_settings.py`."""
    return run_async_entrypoint(async_main)


if __name__ == "__main__":
    raise SystemExit(main())
