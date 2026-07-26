#!/usr/bin/env bash

set -Eeuo pipefail

CLEAN_SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly CLEAN_SCRIPT_DIR
CLEAN_PROJECT_ROOT=$(cd -- "$CLEAN_SCRIPT_DIR/../.." && pwd)
readonly CLEAN_PROJECT_ROOT
readonly CLEAN_BUILD_ROOT="$CLEAN_PROJECT_ROOT/build"

clean_build_root() {
  local root=$1
  local name
  local directory
  local entry
  local -a managed_directories=(artifacts iso live-build rootfs)

  [[ -n $root && $root != / && -f $root/.gitignore ]] || {
    printf '[ERROR] 拒绝清理无效构建目录: %s\n' "$root" >&2
    return 1
  }
  for name in "${managed_directories[@]}"; do
    directory="$root/$name"
    [[ -d $directory && ! -L $directory && -f $directory/.gitkeep ]] || {
      printf '[ERROR] 构建目录契约损坏: %s\n' "$directory" >&2
      return 1
    }
  done

  while IFS= read -r entry; do
    name=${entry##*/}
    case $name in
      .gitignore|artifacts|iso|live-build|rootfs) ;;
      *) rm -rf -- "$entry" ;;
    esac
  done < <(find "$root" -mindepth 1 -maxdepth 1 -print)

  for name in "${managed_directories[@]}"; do
    directory="$root/$name"
    find "$directory" -mindepth 1 -maxdepth 1 ! -name .gitkeep -exec rm -rf -- {} +
  done
}

main() {
  if [[ ${1:-} != 1 ]]; then
    printf '[ERROR] 清理构建文件需要显式执行 make clean CONFIRM=1\n' >&2
    return 2
  fi
  clean_build_root "$CLEAN_BUILD_ROOT"
  printf '[OK] 已清理 %s 中的生成文件；受控目录和占位文件已保留\n' "$CLEAN_BUILD_ROOT"
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  main "$@"
fi
