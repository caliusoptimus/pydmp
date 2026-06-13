"""Query the full area and zone snapshot with `TransactionQueryAllAreasAndZones`."""

from __future__ import annotations

import argparse

from _example_support import (
    add_common_command_arguments,
    build_manager_from_args,
    print_transaction_wire_data,
    print_zone_status_reply,
    run_async_entrypoint,
)
from pydmp.core import TransactionQueryAllAreasAndZones, ZoneStatusReply


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for this example."""
    parser = argparse.ArgumentParser(
        description="Query all areas and zones with TransactionQueryAllAreasAndZones."
    )
    add_common_command_arguments(parser)
    return parser


async def async_main() -> int:
    """Run the example."""
    args = build_parser().parse_args()
    manager = build_manager_from_args(args)

    try:
        transaction = await manager.submit(TransactionQueryAllAreasAndZones())
        reply = transaction.parsed_response
        if not isinstance(reply, ZoneStatusReply):
            raise ValueError("All-areas-and-zones transaction completed without a parsed reply")

        print_zone_status_reply(reply)

        if args.show_raw:
            print_transaction_wire_data(transaction.wire_requests, transaction.wire_responses)
    finally:
        await manager.close()

    return 0


def main() -> int:
    """Synchronous entrypoint used by `python3 query_all_areas_and_zones.py`."""
    return run_async_entrypoint(async_main)


if __name__ == "__main__":
    raise SystemExit(main())
