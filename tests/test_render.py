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
        tool_schemas=[],
        toolset_map={},
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

