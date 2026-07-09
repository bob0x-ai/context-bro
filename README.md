# Context Bro

Standalone Hermes plugin for inspecting prompt/context size.

## Commands

- `hermes context-inspect`
- `/context`

## Usage

- `hermes context-inspect` inspects the latest session for the `default` Hermes profile unless you pass `--agent <profile>`.
- `/context` inspects the current runtime session in the profile where it is invoked.
- `--help` shows usage and examples for both the CLI command and the slash command.
- `--focus <node>` drills into a subtree such as `tools.terminal`.
- `--depth <n>` limits how deep the tree is rendered.
- `--json` emits machine-readable output.

## What it shows

- system prompt tiers and their major sub-blocks
- per-tool schema sizes
- optional session-history totals from `state.db`
- JSON output for cron jobs and automation
