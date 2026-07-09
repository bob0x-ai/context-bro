from __future__ import annotations

import json
from typing import Iterable

from .core import ContextReport, ContextTreeNode


def _fmt_tokens(value: int) -> str:
    return f"{value:,}"


def _fmt_bytes(value: int) -> str:
    return f"{value:,}"


def _iter_nodes(node: ContextTreeNode, depth: int = 0) -> list[tuple[int, ContextTreeNode]]:
    rows = [(depth, node)]
    for child in node.children:
        rows.extend(_iter_nodes(child, depth + 1))
    return rows


def _normalize(value: str) -> str:
    return value.strip().lower()


def _path_to_node(root: ContextTreeNode, target_id: str) -> list[ContextTreeNode]:
    if root.id == target_id:
        return [root]
    for child in root.children:
        path = _path_to_node(child, target_id)
        if path:
            return [root, *path]
    return []


def _select_focus_node(
    root: ContextTreeNode,
    focus: str | None,
) -> tuple[ContextTreeNode, list[ContextTreeNode], str | None]:
    if not focus:
        return root, [root], None

    query = _normalize(focus)
    all_nodes = _iter_nodes(root)

    exact_id_matches = [node for _, node in all_nodes if _normalize(node.id) == query]
    if exact_id_matches:
        node = max(exact_id_matches, key=lambda n: (len(_path_to_node(root, n.id)), -n.tokens))
        return node, _path_to_node(root, node.id), focus

    exact_label_matches = [node for _, node in all_nodes if _normalize(node.label) == query]
    if exact_label_matches:
        node = max(exact_label_matches, key=lambda n: (len(_path_to_node(root, n.id)), -n.tokens))
        return node, _path_to_node(root, node.id), focus

    substring_matches = [
        node
        for _, node in all_nodes
        if query in _normalize(node.id) or query in _normalize(node.label)
    ]
    if substring_matches:
        node = max(substring_matches, key=lambda n: (len(_path_to_node(root, n.id)), -n.tokens))
        return node, _path_to_node(root, node.id), focus

    return root, [root], focus


def render_table(
    report: ContextReport,
    *,
    max_depth: int = 2,
    focus: str | None = None,
) -> str:
    selected_root, path, focus_query = _select_focus_node(report.root, focus)
    rows = selected_root.flatten(max_depth=max_depth)
    label_width = max((len("  " * depth + node.label) for depth, node in rows), default=12)
    lines: list[str] = []
    lines.append("Context Bro snapshot")
    lines.append(
        f"platform={report.platform}  agent={report.agent_name or 'default'}  "
        f"model={report.model or 'unset'}  session={report.session_id or 'n/a'}  "
        f"session_title={report.session_title or 'untitled'}  "
        f"total={_fmt_tokens(report.total_tokens)} tok"
    )
    if report.session_display_name:
        lines.append(f"session_display_name={report.session_display_name}")
    if focus_query:
        path_text = " > ".join(node.label for node in path)
        lines.append(f"focus={focus_query}  path={path_text}")
    if report.session_source:
        lines.append(f"session_source={report.session_source}")
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


def render_json(report: ContextReport, *, focus: str | None = None) -> str:
    payload = report.to_dict()
    if focus:
        selected_root, path, focus_query = _select_focus_node(report.root, focus)
        payload["focus"] = focus_query
        payload["focus_path"] = [node.id for node in path]
        payload["focus_label_path"] = [node.label for node in path]
        payload["selected_root"] = selected_root.to_dict()
    return json.dumps(payload, ensure_ascii=False, indent=2)
