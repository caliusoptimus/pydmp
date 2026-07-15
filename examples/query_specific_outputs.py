"""Query selected `?WQ` selectors with `TransactionQuerySpecificOutputs`."""

from __future__ import annotations

import argparse

from _example_support import (
    add_common_command_arguments,
    build_manager_from_args,
    normalize_name_for_display,
    print_transaction_wire_data,
    run_async_entrypoint,
)
from pydmp.core import OutputStatusReply, TransactionQuerySpecificOutputs


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for this example."""
    parser = argparse.ArgumentParser(
        description="Query selected output selectors without walking the whole ?WQ namespace."
    )
    add_common_command_arguments(parser)
    parser.add_argument(
        "selectors",
        nargs="+",
        help="One or more output selectors, such as 001, 580, D01, F01, or G01.",
    )
    parser.add_argument(
        "--named-only",
        action="store_true",
        help="Filter returned records to named outputs. Raw page rows remain in all_records.",
    )
    parser.add_argument(
        "--show-all-records",
        action="store_true",
        help="Print every raw row returned by the sampled pages, not just requested selectors.",
    )
    return parser


async def async_main() -> int:
    """Run the example."""
    args = build_parser().parse_args()
    manager = build_manager_from_args(args)

    try:
        transaction = await manager.submit(
            TransactionQuerySpecificOutputs(
                args.selectors,
                named_only=args.named_only,
            )
        )
        reply = transaction.parsed_response
        if not isinstance(reply, OutputStatusReply):
            raise ValueError("Specific-output transaction completed without a parsed reply")

        records = reply.all_records if args.show_all_records else reply.records

        print(f"requested selectors: {', '.join(transaction.selectors)}")
        print(f"complete: {reply.complete}")
        print(f"named_only: {reply.named_only}")
        print(f"returned records: {len(reply.records)}")
        print(f"all raw records: {len(reply.all_records or [])}")
        print(f"raw replies: {len(reply.raw_replies)}")

        print()
        print("selector namespace status name")
        print("-------- --------- ------ ----")
        for record in records:
            print(
                f"{record.selector:>8} {record.namespace:>9} {record.status:^6} "
                f"{normalize_name_for_display(record.name)}"
            )

        if args.show_raw:
            print_transaction_wire_data(transaction.wire_requests, transaction.wire_responses)
    finally:
        await manager.close()

    return 0


def main() -> int:
    """Synchronous entrypoint used by `python3 query_specific_outputs.py`."""
    return run_async_entrypoint(async_main)


if __name__ == "__main__":
    raise SystemExit(main())
