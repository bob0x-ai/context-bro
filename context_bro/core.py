from __future__ import annotations

import dataclasses
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    try:
        from agent.model_metadata import estimate_tokens_rough as _rough

        return int(_rough(text))
    except Exception:
        return (len(text) + 3) // 4


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _measure_text(text: str) -> tuple[int, int]:
    return len(text.encode("utf-8")), _estimate_tokens(text)


def _measure_json(value: Any) -> tuple[int, int, str]:
    text = _json_text(value)
    size, tokens = _measure_text(text)
    return size, tokens, text


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "block"


@dataclass
class ContextTreeNode:
    id: str
    label: str
    kind: str
    source_type: str
    bytes: int = 0
    tokens: int = 0
    parent_id: str | None = None
    share_of_total: float = 0.0
    share_of_parent: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)
    children: list["ContextTreeNode"] = field(default_factory=list)

    @classmethod
    def text(
        cls,
        *,
        id: str,
        label: str,
        kind: str,
        source_type: str,
        text: str,
        parent_id: str | None = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> "ContextTreeNode":
        size, tokens = _measure_text(text)
        return cls(
            id=id,
            label=label,
            kind=kind,
            source_type=source_type,
            bytes=size,
            tokens=tokens,
            parent_id=parent_id,
            meta=dict(meta or {}),
        )

    @classmethod
    def json(
        cls,
        *,
        id: str,
        label: str,
        kind: str,
        source_type: str,
        value: Any,
        parent_id: str | None = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> "ContextTreeNode":
        size, tokens, _ = _measure_json(value)
        return cls(
            id=id,
            label=label,
            kind=kind,
            source_type=source_type,
            bytes=size,
            tokens=tokens,
            parent_id=parent_id,
            meta=dict(meta or {}),
        )

    def add(self, child: "ContextTreeNode") -> "ContextTreeNode":
        child.parent_id = self.id
        self.children.append(child)
        return child

    def aggregate(self) -> "ContextTreeNode":
        if self.children:
            for child in self.children:
                child.aggregate()
            self.bytes = sum(child.bytes for child in self.children)
            self.tokens = sum(child.tokens for child in self.children)
        return self

    def annotate_shares(self, total_tokens: int, parent_tokens: int | None = None) -> None:
        self.share_of_total = (self.tokens / total_tokens * 100.0) if total_tokens else 0.0
        self.share_of_parent = (
            (self.tokens / parent_tokens * 100.0) if parent_tokens else 100.0
        )
        for child in self.children:
            child.annotate_shares(total_tokens=total_tokens, parent_tokens=self.tokens or None)

    def flatten(self, *, max_depth: int | None = None, depth: int = 0) -> list[tuple[int, "ContextTreeNode"]]:
        rows = [(depth, self)]
        if max_depth is None or depth < max_depth:
            for child in self.children:
                rows.extend(child.flatten(max_depth=max_depth, depth=depth + 1))
        return rows

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "source_type": self.source_type,
            "bytes": self.bytes,
            "tokens": self.tokens,
            "share_of_total": round(self.share_of_total, 4),
            "share_of_parent": round(self.share_of_parent, 4),
            "meta": self.meta,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class ContextReport:
    generated_at: str
    platform: str
    agent_name: str
    model: str
    cwd: str
    session_id: str | None
    session_title: str | None
    session_display_name: str | None
    session_source: str | None
    total_bytes: int
    total_tokens: int
    root: ContextTreeNode
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "platform": self.platform,
            "agent_name": self.agent_name,
            "model": self.model,
            "cwd": self.cwd,
            "session_id": self.session_id,
            "session_title": self.session_title,
            "session_display_name": self.session_display_name,
            "session_source": self.session_source,
            "total_bytes": self.total_bytes,
            "total_tokens": self.total_tokens,
            "warnings": self.warnings,
            "root": self.root.to_dict(),
        }


@dataclass
class PromptSnapshot:
    platform: str
    model: str
    cwd: str
    stable: str
    context: str
    volatile: str
    identity: str
    skills_index: str
    nous_subscription: str
    environment_bundle: str
    core_guidance: str
    memory_block: str
    user_profile_block: str
    external_memory_block: str
    timestamp_block: str
    tool_schemas: list[dict[str, Any]]
    toolset_map: dict[str, str]
    agent_name: str = ""
    session_id: str | None = None
    session_display_name: str | None = None
    session_source: str | None = None
    session_messages: list[dict[str, Any]] = field(default_factory=list)
    session_title: str | None = None
    warnings: list[str] = field(default_factory=list)


def _build_prompt_tree(snapshot: PromptSnapshot) -> ContextTreeNode:
    root = ContextTreeNode(
        id="root",
        label="Context snapshot",
        kind="report",
        source_type="report",
    )

    stable = ContextTreeNode(
        id="stable",
        label="Stable system prompt",
        kind="system_prompt",
        source_type="system_prompt",
    )
    stable.add(
        ContextTreeNode.text(
            id="stable.identity",
            label="Identity / SOUL.md",
            kind="system_prompt_block",
            source_type="system_prompt",
            text=snapshot.identity,
        )
    )
    stable.add(
        ContextTreeNode.text(
            id="stable.skills",
            label="Skills index",
            kind="system_prompt_block",
            source_type="system_prompt",
            text=snapshot.skills_index,
        )
    )
    if snapshot.nous_subscription:
        stable.add(
            ContextTreeNode.text(
                id="stable.nous_subscription",
                label="Nous subscription",
                kind="system_prompt_block",
                source_type="system_prompt",
                text=snapshot.nous_subscription,
            )
        )
    if snapshot.environment_bundle:
        stable.add(
            ContextTreeNode.text(
                id="stable.environment",
                label="Environment / posture",
                kind="system_prompt_block",
                source_type="system_prompt",
                text=snapshot.environment_bundle,
            )
        )
    if snapshot.core_guidance:
        stable.add(
            ContextTreeNode.text(
                id="stable.core_guidance",
                label="Core guidance remainder",
                kind="system_prompt_block",
                source_type="system_prompt",
                text=snapshot.core_guidance,
            )
        )
    root.add(stable)

    if snapshot.context:
        context = ContextTreeNode(
            id="context",
            label="Session context",
            kind="system_prompt",
            source_type="system_prompt",
        )
        context.add(
            ContextTreeNode.text(
                id="context.project",
                label="Project context files",
                kind="context_file_bundle",
                source_type="system_prompt",
                text=snapshot.context,
            )
        )
        root.add(context)

    volatile = ContextTreeNode(
        id="volatile",
        label="Volatile prompt",
        kind="system_prompt",
        source_type="system_prompt",
    )
    if snapshot.memory_block:
        volatile.add(
            ContextTreeNode.text(
                id="volatile.memory",
                label="Memory snapshot",
                kind="memory",
                source_type="system_prompt",
                text=snapshot.memory_block,
            )
        )
    if snapshot.user_profile_block:
        volatile.add(
            ContextTreeNode.text(
                id="volatile.user_profile",
                label="User profile",
                kind="profile",
                source_type="system_prompt",
                text=snapshot.user_profile_block,
            )
        )
    if snapshot.external_memory_block:
        volatile.add(
            ContextTreeNode.text(
                id="volatile.external_memory",
                label="External memory provider",
                kind="memory",
                source_type="system_prompt",
                text=snapshot.external_memory_block,
            )
        )
    if snapshot.timestamp_block:
        volatile.add(
            ContextTreeNode.text(
                id="volatile.timestamp",
                label="Timestamp / session / model",
                kind="metadata",
                source_type="system_prompt",
                text=snapshot.timestamp_block,
            )
        )
    root.add(volatile)

    tools_root = ContextTreeNode(
        id="tools",
        label="Tool definitions",
        kind="tool_definitions",
        source_type="tool_definition",
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for tool in snapshot.tool_schemas:
        name = tool.get("function", {}).get("name") or tool.get("name") or "tool"
        toolset = snapshot.toolset_map.get(str(name), "tools")
        grouped[toolset].append(tool)
    for toolset in sorted(grouped):
        items = grouped[toolset]
        group_id = f"tools.{_slugify(toolset)}"
        group = ContextTreeNode(
            id=group_id,
            label=toolset,
            kind="toolset",
            source_type="tool_definition",
        )
        for tool in sorted(items, key=lambda t: str(t.get("function", {}).get("name") or t.get("name") or "")):
            fn = tool.get("function", {}) if isinstance(tool, dict) else {}
            name = str(fn.get("name") or tool.get("name") or "tool")
            group.add(
                ContextTreeNode.json(
                    id=f"{group_id}.{_slugify(name)}",
                    label=name,
                    kind="tool",
                    source_type="tool_definition",
                    value=tool,
                    meta={
                        "toolset": toolset,
                        "description": fn.get("description", ""),
                    },
                )
            )
        tools_root.add(group)
    root.add(tools_root)

    if snapshot.session_messages:
        session = ContextTreeNode(
            id="session",
            label="Session history",
            kind="conversation",
            source_type="conversation",
            meta={
                "session_id": snapshot.session_id,
                "title": snapshot.session_title,
                "message_count": len(snapshot.session_messages),
            },
        )
        role_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for msg in snapshot.session_messages:
            role_groups[str(msg.get("role") or "other")].append(msg)
        for role in sorted(role_groups):
            role_id = f"session.{_slugify(role)}"
            role_node = ContextTreeNode(
                id=role_id,
                label=f"{role} messages",
                kind="conversation_role",
                source_type="conversation",
            )
            for index, msg in enumerate(role_groups[role], start=1):
                label = f"#{index} {role}"
                tool_name = msg.get("tool_name")
                if tool_name:
                    label = f"{label} · {tool_name}"
                leaf = ContextTreeNode.text(
                    id=f"{role_id}.{index}",
                    label=label,
                    kind="conversation_message",
                    source_type="conversation",
                    text=str(msg.get("rendered", "")),
                    meta={
                        "message_id": msg.get("id"),
                        "timestamp": msg.get("timestamp"),
                        "tool_name": tool_name,
                        "finish_reason": msg.get("finish_reason"),
                    },
                )
                token_count = int(msg.get("token_count") or 0)
                if token_count > 0:
                    leaf.tokens = token_count
                role_node.add(leaf)
            session.add(role_node)
        root.add(session)

    root.aggregate()
    root.annotate_shares(total_tokens=root.tokens or 1)
    return root


def _subtract_blocks(haystack: str, blocks: Iterable[str]) -> str:
    remaining = haystack
    for block in sorted((b for b in blocks if b), key=len, reverse=True):
        remaining = remaining.replace(block, "", 1)
    parts = [part.strip() for part in remaining.split("\n\n") if part.strip()]
    return "\n\n".join(parts)


def build_context_report(snapshot: PromptSnapshot) -> ContextReport:
    root = _build_prompt_tree(snapshot)
    return ContextReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        platform=snapshot.platform,
        agent_name=getattr(snapshot, "agent_name", ""),
        model=snapshot.model,
        cwd=snapshot.cwd,
        session_id=snapshot.session_id,
        session_title=snapshot.session_title,
        session_display_name=getattr(snapshot, "session_display_name", None),
        session_source=getattr(snapshot, "session_source", None),
        total_bytes=root.bytes,
        total_tokens=root.tokens,
        root=root,
        warnings=list(snapshot.warnings),
    )
