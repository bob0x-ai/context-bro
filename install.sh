#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
plugin_name="context-bro"
skill_name="context-inspect"
hermes_home="${HERMES_HOME:-${HOME}/.hermes}"
plugin_root="${hermes_home}/plugins"
skill_root="${hermes_home}/skills"
plugin_target="${plugin_root}/${plugin_name}"
skill_source="${repo_dir}/skills/${skill_name}"
skill_target="${skill_root}/${skill_name}"
skill_file="${skill_target}/SKILL.md"

ensure_dir() {
  if [ ! -d "$1" ]; then
    mkdir -p "$1"
  fi
}

is_context_bro_plugin() {
  [ -f "$1/plugin.yaml" ] && grep -q "^name: context-bro$" "$1/plugin.yaml" 2>/dev/null
}

ensure_dir "${plugin_root}"
ensure_dir "${skill_root}"

if [ -L "${plugin_target}" ] || [ ! -e "${plugin_target}" ]; then
  ln -sfn "${repo_dir}" "${plugin_target}"
elif [ -d "${plugin_target}" ] && is_context_bro_plugin "${plugin_target}"; then
  :
else
  printf 'Cannot install plugin because this path is already in use: %s\n' "${plugin_target}" >&2
  printf 'Move it aside or remove it, then rerun ./install.sh.\n' >&2
  exit 1
fi

if [ -L "${skill_target}" ]; then
  rm "${skill_target}"
fi

if [ ! -e "${skill_target}" ]; then
  ensure_dir "${skill_target}"
fi

if [ -d "${skill_target}" ]; then
  if [ ! -e "${skill_file}" ] || grep -q "author: context-bro" "${skill_file}" 2>/dev/null; then
    cp "${skill_source}/SKILL.md" "${skill_file}"
  else
    printf 'Cannot install normal skill because this path is already in use: %s\n' "${skill_file}" >&2
    printf 'The plugin skill remains available as context-bro:context-inspect.\n' >&2
    exit 1
  fi
else
  printf 'Cannot install normal skill because this path is already in use: %s\n' "${skill_target}" >&2
  printf 'The plugin skill remains available as context-bro:context-inspect.\n' >&2
  exit 1
fi

if command -v hermes >/dev/null 2>&1; then
  hermes plugins enable "${plugin_name}" >/dev/null 2>&1 || true
fi

printf 'Installed plugin %s -> %s\n' "${plugin_target}" "${repo_dir}"
printf 'Installed skill %s from %s\n' "${skill_target}" "${skill_source}"
printf 'Restart Hermes gateway so the new command is picked up: hermes gateway restart\n'
