from context_bro.core import PromptSnapshot, build_context_report
from context_bro.render import render_json, render_table


def _report():
    snapshot = PromptSnapshot(
        platform="cli",
        model="m",
        cwd="/tmp",
        stable="a",
        context="b",
        volatile="c",
        identity="a",
        skills_index="",
        nous_subscription="",
        environment_bundle="",
        core_guidance="",
        memory_block="",
        user_profile_block="",
        external_memory_block="",
        timestamp_block="c",
        tool_schemas=[
            {"type": "function", "function": {"name": "browser_navigate", "description": "Browser", "parameters": {"type": "object"}}},
            {"type": "function", "function": {"name": "terminal", "description": "Terminal", "parameters": {"type": "object"}}},
        ],
        toolset_map={"browser_navigate": "browser", "terminal": "terminal"},
        session_messages=[],
    )
    return build_context_report(snapshot)


def test_render_table_contains_summary_and_rows() -> None:
    text = render_table(_report())
    assert "Context Bro snapshot" in text
    assert "Stable system prompt" in text


def test_render_json_is_valid() -> None:
    text = render_json(_report())
    assert '"generated_at"' in text
    assert '"root"' in text


def test_render_table_focuses_on_matching_subtree() -> None:
    text = render_table(_report(), focus="tools.terminal")
    assert "focus=tools.terminal" in text
    assert "terminal" in text
    assert "browser" not in text


def test_render_json_includes_focus_metadata() -> None:
    text = render_json(_report(), focus="tools.terminal")
    assert '"focus": "tools.terminal"' in text
    assert '"selected_root"' in text
