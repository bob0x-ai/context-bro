from context_bro.adapters import RuntimeSnapshot, snapshot_to_prompt_snapshot
from context_bro.core import ContextTreeNode, PromptSnapshot, build_context_report


def test_report_builds_tree_and_rolls_up_totals() -> None:
    snapshot = PromptSnapshot(
        platform="cli",
        model="test-model",
        cwd="/tmp/work",
        stable="identity\n\nskills\n\ncore guidance",
        context="project context",
        volatile="memory\n\nuser\n\ntimestamp",
        identity="identity",
        skills_index="skills",
        nous_subscription="",
        environment_bundle="",
        core_guidance="core guidance",
        memory_block="memory",
        user_profile_block="user",
        external_memory_block="",
        timestamp_block="timestamp",
        tool_schemas=[
            {"type": "function", "function": {"name": "alpha", "description": "A", "parameters": {"type": "object"}}},
            {"type": "function", "function": {"name": "beta", "description": "B", "parameters": {"type": "object"}}},
        ],
        toolset_map={"alpha": "terminal", "beta": "mcp-github"},
        session_id="sess-1",
        session_messages=[
            {"role": "user", "rendered": "hello", "token_count": 3, "timestamp": 1},
            {"role": "tool", "rendered": "world", "token_count": 4, "timestamp": 2, "tool_name": "alpha"},
        ],
    )

    report = build_context_report(snapshot)

    assert report.total_tokens > 0
    assert report.root.tokens == report.total_tokens
    assert [child.id for child in report.root.children] == ["stable", "context", "volatile", "tools", "session"]
    tools = next(child for child in report.root.children if child.id == "tools")
    assert tools.tokens == sum(child.tokens for child in tools.children)
    assert tools.children[0].children[0].label in {"alpha", "beta"}
    session = next(child for child in report.root.children if child.id == "session")
    assert session.meta["session_id"] == "sess-1"
    assert session.tokens == 7


def test_snapshot_conversion_preserves_runtime_fields() -> None:
    runtime = RuntimeSnapshot(
        platform="cli",
        model="model-x",
        cwd="/tmp/work",
        stable="stable",
        context="context",
        volatile="volatile",
        identity="id",
        skills_index="skills",
        nous_subscription="nous",
        environment_bundle="env",
        core_guidance="core",
        memory_block="mem",
        user_profile_block="user",
        external_memory_block="ext",
        timestamp_block="stamp",
        tool_schemas=[],
        toolset_map={},
        session_id=None,
        session_title=None,
        session_messages=[],
        warnings=["warn"],
    )
    prompt = snapshot_to_prompt_snapshot(runtime)
    assert prompt.model == "model-x"
    assert prompt.environment_bundle == "env"
    assert prompt.warnings == ["warn"]

