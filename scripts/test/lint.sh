#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
readonly PROJECT_ROOT
cd "$PROJECT_ROOT"

mapfile_supported=0
if help mapfile >/dev/null 2>&1; then
  mapfile_supported=1
fi

if [[ $mapfile_supported == 1 ]]; then
  mapfile -t shell_files < <(find scripts -type f -name '*.sh' -print | sort)
else
  shell_files=()
  while IFS= read -r file; do
    shell_files+=("$file")
  done < <(find scripts -type f -name '*.sh' -print | sort)
fi

bash -n "${shell_files[@]}"
printf '[OK] Bash 语法检查通过（%s 个文件）\n' "${#shell_files[@]}"

python3 scripts/test/validate_product.py
python3 scripts/test/validate_experience.py
python3 scripts/test/repository_hygiene.py

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck "${shell_files[@]}"
  printf '[OK] ShellCheck 通过\n'
elif [[ ${STRICT:-0} == 1 ]]; then
  printf '[ERROR] 严格 lint 需要 ShellCheck\n' >&2
  exit 1
else
  printf '[WARN] 未安装 ShellCheck，已跳过；CI 和严格检查不会跳过\n'
fi
