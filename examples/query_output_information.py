"""Query lowercase `?Zi` Output Information rows."""

from __future__ import annotations

import argparse

from _example_support import (
    add_common_command_arguments,
    build_manager_from_args,
    normalize_name_for_display,
    print_transaction_wire_data,
    run_async_entrypoint,
)
from pydmp.core import OutputInformationReply, TransactionQueryOutputInformation


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for this example."""
    parser = argparse.ArgumentParser(
        description="Query output information with lowercase ?Zi."
    )
    add_common_command_arguments(parser)
    parser.add_argument(
        "--start-selector",
        default="001",
        help="Starting selector, such as 001, 450, 480, or 580.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Hard stop for page collection. The default is intentionally generous.",
    )
    return parser


def _format_optional_bool(value: bool | None) -> str:
    """Format optional booleans in the compact table style used by examples."""
    if value is True:
        return "Y"
    if value is False:
        return "N"
    return "-"


async def async_main() -> int:
    """Run the example."""
    args = build_parser().parse_args()
    manager = build_manager_from_args(args)

    try:
        transaction = await manager.submit(
            TransactionQueryOutputInformation(
                args.start_selector,
                max_pages=args.max_pages,
            )
        )
        reply = transaction.parsed_response
        if not isinstance(reply, OutputInformationReply):
            raise ValueError("Output-information transaction completed without a parsed reply")

        print(f"complete: {reply.complete}")
        print(f"records: {len(reply.records)}")
        print(f"local outputs: {len(reply.outputs)}")
        print(f"backend records: {len(reply.backend_records)}")
        print(f"raw replies: {len(reply.raw_replies)}")

        print()
        print("selector kind    rt  backend   sup  trip name")
        print("-------- ------- --- -------- ---- ---- ----")
        for record in reply.records:
            kind = "backend" if record.backend_linked else "local"
            backend = record.backend_serial or "-"
            supervision = (
                str(record.supervision_time_minutes)
                if record.supervision_time_minutes is not None
                else record.supervision_time_code
            )
            print(
                f"{record.selector:>8} {kind:<7} "
                f"{_format_optional_bool(record.output_real_time_status_enabled):^3} "
                f"{backend:>8} {supervision:>4} "
                f"{_format_optional_bool(record.trip_with_panel_bell_enabled):^4} "
                f"{normalize_name_for_display(record.name)}"
            )

        if args.show_raw:
            print_transaction_wire_data(transaction.wire_requests, transaction.wire_responses)
    finally:
        await manager.close()

    return 0


def main() -> int:
    """Synchronous entrypoint used by `python3 query_output_information.py`."""
    return run_async_entrypoint(async_main)


if __name__ == "__main__":
    raise SystemExit(main())
