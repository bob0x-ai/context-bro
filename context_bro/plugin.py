from __future__ import annotations

import argparse
import shlex
from typing import Any

from hermes_cli.profiles import get_active_profile_name

from .adapters import load_runtime_snapshot, snapshot_to_prompt_snapshot
from .core import build_context_report
from .render import render_json, render_table


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="context-inspect",
        add_help=False,
        description="Inspect Hermes prompt/context cost centers as a hierarchical snapshot.",
        epilog=(
            "Examples:\n"
            "  /context --help\n"
            "  /context --focus tools.terminal --depth 1\n"
            "  /context --json --no-session"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--platform", default="cli")
    parser.add_argument("--cwd", default=None)
    parser.add_argument("--agent", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--focus", default=None)
    parser.add_argument("--no-session", action="store_true")
    parser.add_argument("--max-depth", "--depth", type=int, default=2)
    parser.add_argument("--help", action="store_true")
    return parser


def _run_from_args(args: argparse.Namespace) -> str:
    if getattr(args, "help", False):
        return _build_parser().format_help().rstrip()
    snapshot = load_runtime_snapshot(
        platform=getattr(args, "platform", "cli") or "cli",
        cwd=getattr(args, "cwd", None),
        agent=getattr(args, "agent", None) or get_active_profile_name(),
        include_session=not bool(getattr(args, "no_session", False)),
        session_id=getattr(args, "session_id", None),
    )
    report = build_context_report(snapshot_to_prompt_snapshot(snapshot))
    if getattr(args, "json", False):
        return render_json(report, focus=getattr(args, "focus", None))
    return render_table(
        report,
        max_depth=getattr(args, "max_depth", 2) or 2,
        focus=getattr(args, "focus", None),
    )


def _handle_cli(args: argparse.Namespace) -> None:
    print(_run_from_args(args))


def _setup_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    parser.add_argument("--platform", default="cli", help="Hermes platform to inspect")
    parser.add_argument("--cwd", default=None, help="Working directory used for context-file discovery")
    parser.add_argument("--agent", default=None, help="Inspect the latest session for a Hermes profile")
    parser.add_argument("--session-id", default=None, help="Inspect a specific session from state.db")
    parser.add_argument("--focus", default=None, help="Render only the matching subtree")
    parser.add_argument("--no-session", action="store_true", help="Skip state.db session-history inspection")
    parser.add_argument("--max-depth", "--depth", type=int, default=2, help="Maximum tree depth to render in text mode")
    parser.add_argument("--help", action="store_true", help="Show usage and exit")
    parser.set_defaults(func=_handle_cli)


def _handle_slash(raw_args: str) -> str:
    parser = _build_parser()
    argv = shlex.split(raw_args or "")
    args = parser.parse_args(argv)
    return _run_from_args(args)


def register(ctx) -> None:
    ctx.register_cli_command(
        name="context-inspect",
        help="Inspect Hermes prompt/context blocks and tool schemas",
        setup_fn=_setup_cli,
        handler_fn=_handle_cli,
        description="Hierarchical system-prompt and tool-definition inspector",
    )
    ctx.register_command(
        "context",
        handler=_handle_slash,
        description="Inspect prompt/context blocks and tool schemas",
        args_hint="[--json] [--help] [--focus <node>] [--depth <n>] [--session-id <id>] [--no-session]",
    )
