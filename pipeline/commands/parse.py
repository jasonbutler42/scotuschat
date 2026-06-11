"""
Pipeline parse command — stub implementation.

Will be fully implemented in Plan 04 (pipeline parse step: pdfplumber extraction
+ rule-based state machine + instructor/Claude corrective pass → utterance rows).
"""


async def run_parse(args) -> None:
    """
    Parse a previously ingested transcript PDF into utterance rows.

    Args:
        args: argparse.Namespace with:
            - run_id (int): pipeline_run.id from a prior ingest step
            - dry_run (bool): if True, parse but do not write to DB

    This is a stub — full implementation in Plan 04.
    """
    print(f"parse command: run_id={args.run_id}, dry_run={args.dry_run}")
    print("NOTE: parse command is not yet implemented (Plan 04)")
