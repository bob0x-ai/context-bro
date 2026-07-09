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

mkdir -p "${plugin_root}" "${skill_root}"

if [ -L "${plugin_target}" ] || [ ! -e "${plugin_target}" ]; then
  ln -sfn "${repo_dir}" "${plugin_target}"
else
  printf 'Plugin target already exists and is not a symlink: %s\n' "${plugin_target}" >&2
  printf 'Leaving it untouched. Remove it manually if you want this script to replace it.\n' >&2
fi

if [ -L "${skill_target}" ]; then
  rm "${skill_target}"
fi

if [ ! -e "${skill_target}" ]; then
  mkdir -p "${skill_target}"
fi

if [ -d "${skill_target}" ]; then
  if [ ! -e "${skill_file}" ] || grep -q "author: context-bro" "${skill_file}" 2>/dev/null; then
    cp "${skill_source}/SKILL.md" "${skill_file}"
  else
    printf 'Skill target already exists and does not look managed by context-bro: %s\n' "${skill_target}" >&2
    printf 'Leaving it untouched. The plugin skill remains available as context-bro:context-inspect.\n' >&2
  fi
else
  printf 'Skill target already exists and is not a symlink: %s\n' "${skill_target}" >&2
  printf 'Leaving it untouched. The plugin skill remains available as context-bro:context-inspect.\n' >&2
fi

if command -v hermes >/dev/null 2>&1; then
  hermes plugins enable "${plugin_name}" >/dev/null 2>&1 || true
fi

printf 'Installed plugin %s -> %s\n' "${plugin_target}" "${repo_dir}"
printf 'Installed skill %s from %s\n' "${skill_target}" "${skill_source}"
printf 'Restart Hermes gateway so the new command is picked up: hermes gateway restart\n'
