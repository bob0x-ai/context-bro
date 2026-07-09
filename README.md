# Context Bro

`context-bro` is a standalone Hermes plugin that adds:

- `hermes context-inspect`
- `/context`
- `context-bro:context-inspect` plugin skill
- `context-inspect` normal Hermes skill when installed via `install.sh`

It prints a hierarchical snapshot of where prompt space goes, with a focus on the biggest cost centers first:

- system prompt tiers and major sub-blocks
- per-tool schema sizes
- optional session-history totals from `state.db`
- JSON output for cron jobs, scripts, and later drilldown

## Install

The plugin is meant to live outside Hermes core so Hermes updates do not overwrite it. The safest install is a symlink into `${HERMES_HOME:-~/.hermes}/plugins/` that points back to your checkout.

### Quick install

```bash
git clone https://github.com/bob0x-ai/context-bro.git
cd context-bro
./install.sh
```

What the script does:

- creates or refreshes `${HERMES_HOME:-~/.hermes}/plugins/context-bro -> <this checkout>`
- installs `${HERMES_HOME:-~/.hermes}/skills/context-inspect/SKILL.md` from the packaged skill
- enables the plugin in Hermes if needed
- prints a reminder to restart the gateway so the new command and slash alias surface everywhere

The normal skill install is what makes casual prompts like "inspect your context" more likely to work: the same guidance is available both as the explicit plugin skill `context-bro:context-inspect` and as the normal skill `context-inspect`.

### Manual install

Equivalent manual steps:

```bash
repo_dir="$(pwd)"
hermes_home="${HERMES_HOME:-$HOME/.hermes}"
install -d "$hermes_home/plugins" "$hermes_home/skills/context-inspect"
ln -sfn "$repo_dir" "$hermes_home/plugins/context-bro"
install -m 0644 "$repo_dir/skills/context-inspect/SKILL.md" "$hermes_home/skills/context-inspect/SKILL.md"
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
- `skill_view("context-bro:context-inspect")` gives an agent the operating notes for the CLI command.
- `skill_view("context-inspect")` works after `install.sh` installs the packaged skill into the normal Hermes skills directory.
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
