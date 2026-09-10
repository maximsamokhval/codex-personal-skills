#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/.." && pwd -P)"
skills_source="$repo_root/skills"

fail() {
  printf 'Помилка: %s\n' "$*" >&2
  exit 1
}

resolve_target_dir() {
  if [[ -n "${CODEX_SKILLS_DIR:-}" ]]; then
    printf '%s\n' "$CODEX_SKILLS_DIR"
  elif [[ -d "$HOME/.codex" || ! -d "$HOME/.agents" ]]; then
    printf '%s\n' "$HOME/.codex/skills"
  else
    printf '%s\n' "$HOME/.agents/skills"
  fi
}

[[ -d "$skills_source" ]] || fail "Не знайдено skills у репозиторії: $skills_source"

target_dir="$(resolve_target_dir)"
mkdir -p -- "$target_dir"

staging_dir="$(mktemp -d "${TMPDIR:-/tmp}/codex-personal-skills.XXXXXX")"
installation_complete=0
installed_names=()
cleanup() {
  if ((installation_complete == 0)); then
    for skill_name in "${installed_names[@]}"; do
      destination="$target_dir/$skill_name"
      backup="$staging_dir/.backup-$skill_name"
      if [[ -e "$backup" ]]; then
        rm -rf -- "$destination"
        mv -- "$backup" "$destination"
      else
        rm -rf -- "$destination"
      fi
    done
  fi
  rm -rf -- "$staging_dir"
}
trap cleanup EXIT

skill_names=()
while IFS= read -r -d '' source_skill; do
  skill_name="$(basename -- "$source_skill")"
  [[ -f "$source_skill/SKILL.md" ]] || fail "У skill відсутній SKILL.md: $skill_name"
  cp -R -- "$source_skill" "$staging_dir/$skill_name"
  [[ -f "$staging_dir/$skill_name/SKILL.md" ]] || fail "Не вдалося підготувати skill: $skill_name"
  skill_names+=("$skill_name")
done < <(find "$skills_source" -mindepth 1 -maxdepth 1 -type d -print0)

((${#skill_names[@]} > 0)) || fail "У репозиторії немає директорій skills для встановлення"

# Зберігаємо поточні копії до повної перевірки нових, щоб помилка не втратила skill.
for skill_name in "${skill_names[@]}"; do
  destination="$target_dir/$skill_name"
  backup="$staging_dir/.backup-$skill_name"
  if [[ -e "$destination" ]]; then
    mv -- "$destination" "$backup"
  fi
  if ! mv -- "$staging_dir/$skill_name" "$destination"; then
    [[ -e "$backup" ]] && mv -- "$backup" "$destination"
    fail "Не вдалося встановити skill: $skill_name"
  fi
  installed_names+=("$skill_name")
done

for skill_name in "${skill_names[@]}"; do
  [[ -d "$target_dir/$skill_name" ]] || fail "Відсутня директорія встановленого skill: $skill_name"
  [[ -f "$target_dir/$skill_name/SKILL.md" ]] || fail "У встановленому skill відсутній SKILL.md: $skill_name"
done

for skill_name in "${skill_names[@]}"; do
  rm -rf -- "$staging_dir/.backup-$skill_name"
done
installation_complete=1

printf 'Цільовий каталог: %s\nВстановлені skills:\n' "$target_dir"
printf '  - %s\n' "${skill_names[@]}"
