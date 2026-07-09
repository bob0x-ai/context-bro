from context_bro.adapters import RuntimeSnapshot, snapshot_to_prompt_snapshot
from context_bro.core import ContextTreeNode, PromptSnapshot, build_context_report


def test_report_builds_tree_and_rolls_up_totals() -> None:
    snapshot = PromptSnapshot(
        platform="cli",
        agent_name="default",
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
        session_display_name="Daniel Briano",
        session_source="telegram",
        session_messages=[
            {"role": "user", "rendered": "hello", "token_count": 3, "timestamp": 1},
            {"role": "tool", "rendered": "world", "token_count": 4, "timestamp": 2, "tool_name": "alpha"},
        ],
    )

    report = build_context_report(snapshot)

    assert report.total_tokens > 0
    assert report.root.tokens == report.total_tokens
    assert [child.id for child in report.root.children] == ["stable", "context", "volatile", "tools", "session"]
    assert report.agent_name == "default"
    assert report.session_title is None
    assert report.session_display_name == "Daniel Briano"
    assert report.session_source == "telegram"
    tools = next(child for child in report.root.children if child.id == "tools")
    assert tools.tokens == sum(child.tokens for child in tools.children)
    assert tools.children[0].children[0].label in {"alpha", "beta"}
    session = next(child for child in report.root.children if child.id == "session")
    assert session.meta["session_id"] == "sess-1"
    assert session.tokens == 7


def test_snapshot_conversion_preserves_runtime_fields() -> None:
    runtime = RuntimeSnapshot(
        platform="cli",
        agent_name="writer",
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
        session_display_name=None,
        session_source=None,
        session_messages=[],
        warnings=["warn"],
    )
    prompt = snapshot_to_prompt_snapshot(runtime)
    assert prompt.agent_name == "writer"
    assert prompt.model == "model-x"
    assert prompt.environment_bundle == "env"
    assert prompt.warnings == ["warn"]


def test_session_snapshot_uses_requested_agent_profile(tmp_path, monkeypatch) -> None:
    import sqlite3

    hermes_home = tmp_path / ".hermes"
    writer_home = hermes_home / "profiles" / "writer"
    writer_home.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    db = sqlite3.connect(writer_home / "state.db")
    try:
        db.execute(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT,
                display_name TEXT,
                started_at REAL NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                tool_call_id TEXT,
                tool_calls TEXT,
                tool_name TEXT,
                timestamp REAL NOT NULL,
                token_count INTEGER,
                finish_reason TEXT,
                reasoning TEXT,
                reasoning_content TEXT,
                reasoning_details TEXT,
                codex_reasoning_items TEXT,
                codex_message_items TEXT,
                platform_message_id TEXT,
                observed INTEGER DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                compacted INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        db.execute(
            "INSERT INTO sessions (id, source, title, display_name, started_at) VALUES (?, ?, ?, ?, ?)",
            ("writer-1", "cli", "Writer session", "Writer", 1.0),
        )
        db.commit()
    finally:
        db.close()

    from context_bro.adapters import _load_session_snapshot

    agent_name, session_id, session_title, session_display_name, messages = _load_session_snapshot(
        None,
        agent_name="writer",
    )

    assert agent_name == "writer"
    assert session_id == "writer-1"
    assert session_title == "Writer session"
    assert session_display_name == "Writer"
    assert messages == []
