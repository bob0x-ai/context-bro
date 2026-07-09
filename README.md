# Context Bro

`context-bro` is a standalone Hermes plugin that adds:

- `hermes context-inspect`
- `/context`

It prints a hierarchical snapshot of where prompt space goes, with a focus on the biggest cost centers first:

- system prompt tiers and major sub-blocks
- per-tool schema sizes
- optional session-history totals from `state.db`
- JSON output for cron jobs, scripts, and later drilldown

## Install

The plugin is meant to live outside Hermes core so Hermes updates do not overwrite it. The safest install is a symlink into `~/.hermes/plugins/` that points back to this repo.

### Quick install

```bash
cd /home/ubuntu/projects/context-bro
./install.sh
```

What the script does:

- creates or refreshes `~/.hermes/plugins/context-bro -> /home/ubuntu/projects/context-bro`
- enables the plugin in Hermes if needed
- prints a reminder to restart the gateway so the new command surfaces everywhere

### Manual install

```bash
mkdir -p ~/.hermes/plugins
ln -sfn /home/ubuntu/projects/context-bro ~/.hermes/plugins/context-bro
hermes plugins enable context-bro
hermes gateway restart
```

After restart, verify the command is available:

```bash
hermes context-inspect --help
hermes context-inspect
```

## Usage

- `hermes context-inspect` inspects the latest session for the `default` profile when no `--agent` is provided.
- `hermes context-inspect --agent <profile>` inspects the latest session for a specific Hermes profile.
- `/context` inspects the session in the runtime where it was invoked.
- `--help` shows usage and examples for both the CLI command and the slash command.
- `--focus <node>` drills into a subtree such as `tools.terminal`.
- `--depth <n>` limits how deep the tree is rendered.
- `--json` emits machine-readable output.

## Session Selection

`context-bro` chooses the session in a simple, explicit way:

1. If you pass `--session-id`, it inspects that exact session.
2. Otherwise it looks at the selected agent profile.
3. If no `--agent` is given, it falls back to the `default` profile.
4. If `state.db` is missing or unreadable, the command still runs and shows the live prompt snapshot without session-history totals.

The output includes both:

- `session_title`, which is Hermes' session name
- `session_display_name`, which is the human-facing agent/session label when Hermes stores one

That makes it easier to tell *which* session was inspected, not just which database row was used.

## `state.db` totals

The optional session-history block comes from Hermes' SQLite session store:

- the plugin reads `state.db` from the selected profile home
- it loads the chosen session's `messages` rows in timestamp order
- message `token_count` values are used when Hermes recorded them
- if a row has no stored token count, the plugin estimates tokens from the rendered text so the report still stays useful

This means the snapshot still works on older or partial databases, but it gets more precise when Hermes has persisted message token counts.

## Output

The command renders a tree-shaped snapshot so drilldown can be added later without changing the core model:

- each row has a stable node id
- parents and children are explicit
- tokens, bytes, and share are rolled up from the leaves
- JSON mirrors the same tree for automation and later UI work
