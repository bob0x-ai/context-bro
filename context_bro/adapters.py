from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .core import PromptSnapshot, _subtract_blocks


def _hermes_home() -> Path:
    raw = os.environ.get("HERMES_HOME")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".hermes"


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _tool_name(tool: dict[str, Any]) -> str:
    fn = tool.get("function") if isinstance(tool, dict) else None
    if isinstance(fn, dict):
        return str(fn.get("name") or "")
    return str(tool.get("name") or "")


def _decode_content(value: Any) -> Any:
    prefix = "\x00json:"
    if isinstance(value, str) and value.startswith(prefix):
        try:
            return json.loads(value[len(prefix) :])
        except Exception:
            return value
    return value


def _resolve_session_db_path() -> Path:
    return _hermes_home() / "state.db"


def _load_latest_session_id(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT id FROM sessions ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return str(row[0] if not isinstance(row, sqlite3.Row) else row["id"])


def _load_session_snapshot(session_id: str | None) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    path = _resolve_session_db_path()
    if not path.exists():
        return None, None, []
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
    except Exception:
        return None, None, []
    try:
        if not session_id:
            session_id = _load_latest_session_id(conn)
        if not session_id:
            return None, None, []
        row = conn.execute(
            "SELECT id, title FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None, None, []
        messages = []
        for msg in conn.execute(
            """
            SELECT id, role, content, tool_name, tool_calls, tool_call_id,
                   token_count, finish_reason, reasoning, reasoning_content,
                   timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC, id ASC
            """,
            (session_id,),
        ).fetchall():
            content = _decode_content(msg["content"])
            rendered = content
            if isinstance(rendered, (dict, list)):
                rendered = _json_text(rendered)
            elif rendered is None:
                rendered = ""
            rendered = str(rendered)
            token_count = msg["token_count"]
            if token_count is None:
                token_count = max(1, (len(rendered) + 3) // 4) if rendered else 0
            messages.append(
                {
                    "id": msg["id"],
                    "role": msg["role"] or "other",
                    "rendered": rendered,
                    "tool_name": msg["tool_name"],
                    "tool_call_id": msg["tool_call_id"],
                    "token_count": int(token_count or 0),
                    "finish_reason": msg["finish_reason"],
                    "timestamp": msg["timestamp"],
                }
            )
        return str(row["id"]), str(row["title"] or ""), messages
    finally:
        conn.close()


def _run_prompt_size_fallback(platform: str) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["hermes", "prompt-size", "--platform", platform, "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(proc.stdout)
    except Exception:
        return {}


@dataclass
class RuntimeSnapshot:
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
    session_id: str | None
    session_title: str | None
    session_messages: list[dict[str, Any]]
    warnings: list[str]


def _toolset_for_tool(name: str) -> str:
    try:
        from tools.registry import registry

        toolset = registry.get_toolset_for_tool(name)
        return str(toolset or "tools")
    except Exception:
        return "tools"


def load_runtime_snapshot(
    *,
    platform: str = "cli",
    cwd: str | None = None,
    include_session: bool = True,
    session_id: str | None = None,
) -> RuntimeSnapshot:
    cwd = cwd or os.getcwd()
    warnings: list[str] = []
    model = ""

    identity = ""
    skills_index = ""
    nous_subscription = ""
    environment_bundle = ""
    core_guidance = ""
    memory_block = ""
    user_profile_block = ""
    external_memory_block = ""
    timestamp_block = ""
    tool_schemas: list[dict[str, Any]] = []
    toolset_map: dict[str, str] = {}
    stable = ""
    context = ""
    volatile = ""

    try:
        from hermes_cli.config import load_config
        from hermes_cli.tools_config import _get_platform_tools
        from run_agent import AIAgent
        from agent.prompt_builder import (
            DEFAULT_AGENT_IDENTITY,
            build_context_files_prompt,
            build_environment_hints,
            build_nous_subscription_prompt,
            build_skills_system_prompt,
            load_soul_md,
        )
        from agent.system_prompt import build_system_prompt_parts
        from hermes_time import now as hermes_now
    except Exception as exc:
        warnings.append(f"hermes imports unavailable: {exc}")
        fallback = _run_prompt_size_fallback(platform)
        return RuntimeSnapshot(
            platform=platform,
            model=str(fallback.get("model") or ""),
            cwd=cwd,
            stable="",
            context="",
            volatile="",
            identity="",
            skills_index="",
            nous_subscription="",
            environment_bundle="",
            core_guidance="",
            memory_block="",
            user_profile_block="",
            external_memory_block="",
            timestamp_block="",
            tool_schemas=[],
            toolset_map={},
            session_id=None,
            session_title=None,
            session_messages=[],
            warnings=warnings,
        )

    cfg = load_config() or {}
    model_cfg = cfg.get("model", {}) if isinstance(cfg.get("model"), dict) else {}
    model = str(model_cfg.get("default") or model_cfg.get("model") or "")
    enabled_toolsets = sorted(_get_platform_tools(cfg, platform))
    disabled_toolsets = (cfg.get("agent") or {}).get("disabled_toolsets") or None

    agent = AIAgent(
        model=model,
        api_key="inspect-only",
        base_url="https://openrouter.ai/api/v1",
        quiet_mode=True,
        save_trajectories=False,
        platform=platform,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
    )

    parts = build_system_prompt_parts(agent)
    stable = parts.get("stable", "") or ""
    context = parts.get("context", "") or ""
    volatile = parts.get("volatile", "") or ""

    soul = load_soul_md(getattr(getattr(agent, "context_compressor", None), "context_length", None))
    identity = soul or DEFAULT_AGENT_IDENTITY

    valid_tool_names = set(getattr(agent, "valid_tool_names", set()) or set())
    toolsets = {
        _toolset_for_tool(name)
        for name in valid_tool_names
    }
    try:
        compact_categories = frozenset()
        try:
            from agent.coding_context import coding_compact_skill_categories

            compact_categories = coding_compact_skill_categories(platform=platform, cwd=cwd)
        except Exception:
            compact_categories = frozenset()
        skills_index = build_skills_system_prompt(
            available_tools=valid_tool_names,
            available_toolsets=toolsets,
            compact_categories=compact_categories or None,
        )
    except Exception as exc:
        warnings.append(f"skills prompt unavailable: {exc}")

    try:
        nous_subscription = build_nous_subscription_prompt(valid_tool_names)
    except Exception as exc:
        warnings.append(f"nous subscription prompt unavailable: {exc}")

    try:
        environment_bundle = build_environment_hints()
    except Exception as exc:
        warnings.append(f"environment hints unavailable: {exc}")

    env_blocks: list[str] = []
    try:
        from agent.coding_context import coding_system_blocks

        env_blocks.extend(
            coding_system_blocks(
                platform=platform,
                cwd=cwd,
                model=model,
            )
        )
    except Exception:
        pass
    try:
        from tools.env_probe import get_environment_probe_line

        probe = get_environment_probe_line()
        if probe:
            env_blocks.append(probe)
    except Exception:
        pass
    try:
        from agent.file_safety import _resolve_active_profile_name

        active_profile = _resolve_active_profile_name()
        if active_profile == "default":
            env_blocks.append(
                "Active Hermes profile: default. Other profiles (if any) live under ~/.hermes/profiles/<name>/. "
                "Each profile has its own skills/, plugins/, cron/, and memories/ that affect a different session than this one."
            )
        else:
            env_blocks.append(
                f"Active Hermes profile: {active_profile}. This session reads and writes ~/.hermes/profiles/{active_profile}/."
            )
    except Exception:
        pass
    if env_blocks:
        environment_bundle = "\n\n".join([environment_bundle, *env_blocks]).strip()

    identity = identity or ""
    stable = stable or ""
    core_guidance = _subtract_blocks(
        stable,
        [identity, skills_index, nous_subscription, environment_bundle],
    )

    try:
        memory_store = getattr(agent, "_memory_store", None)
        if memory_store is not None and getattr(agent, "_memory_enabled", True):
            memory_block = memory_store.format_for_system_prompt("memory") or ""
        if memory_store is not None and getattr(agent, "_user_profile_enabled", True):
            user_profile_block = memory_store.format_for_system_prompt("user") or ""
    except Exception:
        pass

    try:
        memory_manager = getattr(agent, "_memory_manager", None)
        if memory_manager is not None:
            external_memory_block = memory_manager.build_system_prompt() or ""
    except Exception:
        pass

    try:
        stamp = hermes_now()
    except Exception:
        from datetime import datetime

        stamp = datetime.now()
    timestamp_block = f"Conversation started: {stamp.strftime('%A, %B %d, %Y')}"
    if getattr(agent, "pass_session_id", False) and getattr(agent, "session_id", None):
        timestamp_block += f"\nSession ID: {agent.session_id}"
    if model:
        timestamp_block += f"\nModel: {model}"
    provider = getattr(agent, "provider", "")
    if provider:
        timestamp_block += f"\nProvider: {provider}"

    try:
        tool_schemas = list(getattr(agent, "tools", None) or [])
    except Exception as exc:
        warnings.append(f"tool schema inspection unavailable: {exc}")
        tool_schemas = []
    try:
        from tools.registry import registry

        toolset_map = registry.get_tool_to_toolset_map()
    except Exception:
        toolset_map = {(_tool_name(tool)): "tools" for tool in tool_schemas}

    loaded_session_id: str | None = None
    session_title: str | None = None
    session_messages: list[dict[str, Any]] = []
    if include_session:
        try:
            loaded_session_id, session_title, session_messages = _load_session_snapshot(session_id)
        except Exception as exc:
            warnings.append(f"session snapshot unavailable: {exc}")

    return RuntimeSnapshot(
        platform=platform,
        model=model,
        cwd=cwd,
        stable=stable,
        context=context,
        volatile=volatile,
        identity=identity,
        skills_index=skills_index,
        nous_subscription=nous_subscription,
        environment_bundle=environment_bundle,
        core_guidance=core_guidance,
        memory_block=memory_block,
        user_profile_block=user_profile_block,
        external_memory_block=external_memory_block,
        timestamp_block=timestamp_block,
        tool_schemas=tool_schemas,
        toolset_map=toolset_map,
        session_id=loaded_session_id,
        session_title=session_title,
        session_messages=session_messages,
        warnings=warnings,
    )


def snapshot_to_prompt_snapshot(snapshot: RuntimeSnapshot) -> PromptSnapshot:
    return PromptSnapshot(
        platform=snapshot.platform,
        model=snapshot.model,
        cwd=snapshot.cwd,
        stable=snapshot.stable,
        context=snapshot.context,
        volatile=snapshot.volatile,
        identity=snapshot.identity,
        skills_index=snapshot.skills_index,
        nous_subscription=snapshot.nous_subscription,
        environment_bundle=snapshot.environment_bundle,
        core_guidance=snapshot.core_guidance,
        memory_block=snapshot.memory_block,
        user_profile_block=snapshot.user_profile_block,
        external_memory_block=snapshot.external_memory_block,
        timestamp_block=snapshot.timestamp_block,
        tool_schemas=snapshot.tool_schemas,
        toolset_map=snapshot.toolset_map,
        session_id=snapshot.session_id,
        session_messages=snapshot.session_messages,
        session_title=snapshot.session_title,
        warnings=snapshot.warnings,
    )

