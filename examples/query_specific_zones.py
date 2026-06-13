"""Query one seeded `?WB` sweep with `TransactionQuerySpecificZones`."""

from __future__ import annotations

import argparse

from _example_support import (
    add_common_command_arguments,
    build_manager_from_args,
    print_transaction_wire_data,
    print_zone_status_reply,
    run_async_entrypoint,
)
from pydmp.core import TransactionQuerySpecificZones, ZoneStatusReply


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for this example."""
    parser = argparse.ArgumentParser(
        description="Query one area-scoped or wildcard ?WB sweep with TransactionQuerySpecificZones."
    )
    add_common_command_arguments(parser)
    parser.add_argument(
        "--area",
        default="**",
        help="Area selector to seed ?WB with. Use 01-32 for one area, or ** for wildcard.",
    )
    parser.add_argument(
        "--start-zone",
        default="001",
        help="Visible zone selector used in the ?WB seed.",
    )
    parser.add_argument(
        "--end-zone",
        help="Optional inclusive client-side filter for returned zone records.",
    )
    parser.add_argument(
        "--no-global-zones",
        action="store_true",
        help="Use the N flag in the ?WB seed instead of the default Y flag.",
    )
    return parser


async def async_main() -> int:
    """Run the example."""
    args = build_parser().parse_args()
    manager = build_manager_from_args(args)

    try:
        transaction = await manager.submit(
            TransactionQuerySpecificZones(
                args.area,
                start_zone=args.start_zone,
                end_zone=args.end_zone,
                include_global_zones=not args.no_global_zones,
            )
        )
        reply = transaction.parsed_response
        if not isinstance(reply, ZoneStatusReply):
            raise ValueError("Specific-zones transaction completed without a parsed reply")

        print(f"area selector: {transaction.area_number}")
        print(f"start zone: {transaction.start_zone}")
        print(f"end zone: {transaction.end_zone or '<none>'}")
        print(f"include global zones: {transaction.include_global_zones}")
        print_zone_status_reply(reply)

        if args.show_raw:
            print_transaction_wire_data(transaction.wire_requests, transaction.wire_responses)
    finally:
        await manager.close()

    return 0


def main() -> int:
    """Synchronous entrypoint used by `python3 query_specific_zones.py`."""
    return run_async_entrypoint(async_main)


if __name__ == "__main__":
    raise SystemExit(main())
