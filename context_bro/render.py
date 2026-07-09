from __future__ import annotations

import json
from typing import Iterable

from .core import ContextReport, ContextTreeNode


def _fmt_tokens(value: int) -> str:
    return f"{value:,}"


def _fmt_bytes(value: int) -> str:
    return f"{value:,}"


def render_table(report: ContextReport, *, max_depth: int = 2) -> str:
    rows = report.root.flatten(max_depth=max_depth)
    label_width = max((len("  " * depth + node.label) for depth, node in rows), default=12)
    lines: list[str] = []
    lines.append("Context Bro snapshot")
    lines.append(
        f"platform={report.platform}  model={report.model or 'unset'}  "
        f"session={report.session_id or 'n/a'}  total={_fmt_tokens(report.total_tokens)} tok"
    )
    if report.warnings:
        for warning in report.warnings:
            lines.append(f"warning: {warning}")
    lines.append("")
    header = f"{'Block':<{label_width}}  {'Tokens':>12}  {'Bytes':>12}  {'Share':>8}"
    lines.append(header)
    lines.append("-" * len(header))
    for depth, node in rows:
        indent = "  " * depth
        label = f"{indent}{node.label}"
        lines.append(
            f"{label:<{label_width}}  {_fmt_tokens(node.tokens):>12}  "
            f"{_fmt_bytes(node.bytes):>12}  {node.share_of_total:>7.2f}%"
        )
    return "\n".join(lines)


def render_json(report: ContextReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)

