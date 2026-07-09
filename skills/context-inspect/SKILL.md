---
name: context-inspect
description: Use the context-bro Hermes plugin to inspect prompt, tool-schema, and session-history token costs with `hermes context-inspect`.
version: 0.1.0
author: context-bro
platforms: [linux, macos]
metadata:
  hermes:
    tags: [hermes, context, prompt, tokens, tools, diagnostics]
---

# Context Inspect

Use this skill when you need to understand where a Hermes session's context budget is going, especially when tool definitions, system prompt blocks, memory, or session history look unexpectedly large.

The plugin provides the terminal command:

```bash
hermes context-inspect
```

It prints a read-only hierarchical snapshot. It does not mutate prompts, sessions, config, or Hermes core files.

## Common Commands

Inspect the default profile's latest session:

```bash
hermes context-inspect
```

Inspect another Hermes profile:

```bash
hermes context-inspect --agent writer
```

Emit JSON for automation or follow-up analysis:

```bash
hermes context-inspect --json
```

Skip `state.db` session-history inspection and measure only the live prompt/tool snapshot:

```bash
hermes context-inspect --no-session
```

Focus on one subtree:

```bash
hermes context-inspect --focus tools.terminal --depth 1
```

Inspect a specific session row:

```bash
hermes context-inspect --session-id 20260709_211817_5dec86db
```

## How To Interpret Output

- `Stable system prompt` is the reusable prompt prefix, including identity, skill index, environment/posture, and core guidance.
- `Volatile prompt` contains blocks that can change between sessions or turns, such as memory, user profile, external memory provider text, and timestamp/model metadata.
- `Tool definitions` is usually the largest block when many toolsets are enabled; child rows attribute cost by toolset and then by tool.
- `Session history` appears when `state.db` is available and the selected session has persisted messages.

The header identifies the inspected profile and session:

- `agent` is the selected Hermes profile. If no `--agent` is given, the command uses `default`.
- `session` is the selected session id from `state.db`, or `n/a` when session inspection is skipped or unavailable.
- `session_title` is Hermes' stored session title when present.
- `session_display_name` is Hermes' stored display label when present. It may be a user/account label rather than a unique session name.
- `session_source` is the platform that created the session, such as `cli`, `telegram`, or `matrix`.

## Workflow

1. Run `hermes context-inspect` first for a human-readable snapshot.
2. If the snapshot shows tool definitions dominating, inspect the tool rows before changing prompts or memory.
3. Use `--agent <profile>` when comparing profiles with different tools, skills, memories, or config.
4. Use `--json` when you need exact node ids, parent relationships, or repeatable cron output.
5. Use `--no-session` when diagnosing live prompt/tool overhead independently from stored conversation history.

Prefer this command over `hermes prompt-size` when you need per-tool attribution or tree-shaped output. Keep `hermes prompt-size` for legacy compatibility checks.
