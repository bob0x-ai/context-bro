from __future__ import annotations

import argparse
import sys

from .adapters import load_runtime_snapshot, snapshot_to_prompt_snapshot
from .core import build_context_report
from .render import render_json, render_table


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="context-inspect", add_help=True)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    parser.add_argument("--platform", default="cli", help="Hermes platform to inspect")
    parser.add_argument("--cwd", default=None, help="Working directory used for context-file discovery")
    parser.add_argument("--session-id", default=None, help="Inspect a specific session from state.db")
    parser.add_argument(
        "--no-session",
        action="store_true",
        help="Skip state.db session-history inspection",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=2,
        help="Maximum tree depth to render in text mode",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    snapshot = load_runtime_snapshot(
        platform=args.platform,
        cwd=args.cwd,
        include_session=not args.no_session,
        session_id=args.session_id,
    )
    report = build_context_report(snapshot_to_prompt_snapshot(snapshot))
    if args.json:
        sys.stdout.write(render_json(report))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_table(report, max_depth=args.max_depth))
        sys.stdout.write("\n")
    return 0


def main() -> None:
    raise SystemExit(run())

