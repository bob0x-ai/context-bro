#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
plugin_name="context-bro"
plugin_root="${HOME}/.hermes/plugins"
target="${plugin_root}/${plugin_name}"

mkdir -p "${plugin_root}"
ln -sfn "${repo_dir}" "${target}"

if command -v hermes >/dev/null 2>&1; then
  hermes plugins enable "${plugin_name}" >/dev/null 2>&1 || true
fi

printf 'Installed %s -> %s\n' "${target}" "${repo_dir}"
printf 'Restart Hermes gateway so the new command is picked up: hermes gateway restart\n'
