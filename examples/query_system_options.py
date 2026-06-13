"""Query System Options with a direct transaction example."""

from __future__ import annotations

import argparse
from dataclasses import fields

from _example_support import (
    add_common_command_arguments,
    build_manager_from_args,
    format_bytes_for_cli,
    print_section_heading,
    print_transaction_wire_data,
    run_async_entrypoint,
)
from pydmp.core import SystemOptionsReply, TransactionQuerySystemOptions


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for this example."""
    parser = argparse.ArgumentParser(
        description="Query System Options with the new stateless core."
    )
    add_common_command_arguments(parser)
    return parser


def format_value(value) -> str:
    """Render one parsed field value for CLI output."""
    if isinstance(value, bytes):
        return format_bytes_for_cli(value)
    if value is None:
        return "<none>"
    return str(value)


async def async_main() -> int:
    """Run the example."""
    args = build_parser().parse_args()
    manager = build_manager_from_args(args)

    try:
        transaction = await manager.submit(TransactionQuerySystemOptions())
        reply = transaction.parsed_response
        if not isinstance(reply, SystemOptionsReply):
            raise ValueError("System-options transaction completed without a parsed reply")

        print("System Options")
        print("field                         value")
        print("----------------------------- -----")
        for field in fields(reply):
            if field.name in {"raw_body", "raw_reply"}:
                continue
            print(f"{field.name:<29} {format_value(getattr(reply, field.name))}")

        if args.show_raw:
            print_section_heading("Raw Parsed Payload")
            print(f"raw_body:  {format_bytes_for_cli(reply.raw_body)}")
            print(f"raw_reply: {format_bytes_for_cli(reply.raw_reply)}")
            print_transaction_wire_data(transaction.wire_requests, transaction.wire_responses)
    finally:
        await manager.close()

    return 0


def main() -> int:
    """Synchronous entrypoint used by `python3 query_system_options.py`."""
    return run_async_entrypoint(async_main)


if __name__ == "__main__":
    raise SystemExit(main())
