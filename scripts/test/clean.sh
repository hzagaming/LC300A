#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
# shellcheck source=/dev/null
source "$SCRIPT_DIR/../clean/build.sh"

fixture_dir=$(mktemp -d "${TMPDIR:-/tmp}/lc300a-clean.XXXXXX")
readonly fixture_dir
[[ $fixture_dir == */lc300a-clean.* ]] || exit 1
trap 'rm -rf -- "$fixture_dir"' EXIT

touch "$fixture_dir/.gitignore"
for name in artifacts iso live-build rootfs; do
  mkdir -p "$fixture_dir/$name/nested"
  touch "$fixture_dir/$name/.gitkeep"
  touch "$fixture_dir/$name/nested/generated.bin"
done
mkdir -p "$fixture_dir/scratch"
touch "$fixture_dir/scratch/generated.bin"

clean_build_root "$fixture_dir"

for name in artifacts iso live-build rootfs; do
  [[ -d $fixture_dir/$name && -f $fixture_dir/$name/.gitkeep ]] || {
    printf '[ERROR] clean 未保留受控目录: %s\n' "$name" >&2
    exit 1
  }
  [[ $(find "$fixture_dir/$name" -mindepth 1 | wc -l | tr -d ' ') == 1 ]] || {
    printf '[ERROR] clean 未清除生成文件: %s\n' "$name" >&2
    exit 1
  }
done
[[ ! -e $fixture_dir/scratch ]] || {
  printf '[ERROR] clean 未清除未知构建项\n' >&2
  exit 1
}
printf '[OK] 构建清理契约测试通过\n'
