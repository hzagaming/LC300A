#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
# shellcheck source=/dev/null
source "$SCRIPT_DIR/../bootstrap/lib.sh"

fixture_dir=$(mktemp -d "${TMPDIR:-/tmp}/lc300a-os-release.XXXXXX")
readonly fixture_dir
[[ $fixture_dir == */lc300a-os-release.* ]] || exit 1
trap 'rm -rf -- "$fixture_dir"' EXIT

assert_release() {
  local distro=$1
  local version=$2
  local codename=$3
  local expected=$4
  local fixture="$fixture_dir/os-release"
  local actual

  printf 'ID=%s\nVERSION_ID="%s"\nVERSION_CODENAME=%s\n' \
    "$distro" "$version" "$codename" >"$fixture"
  if is_supported_linux_release "$fixture"; then
    actual=0
  else
    actual=1
  fi
  [[ $actual == "$expected" ]] || {
    printf '[ERROR] 发行版契约结果错误: %s %s %s\n' "$distro" "$version" "$codename" >&2
    exit 1
  }
}

assert_release debian 13 trixie 0
assert_release ubuntu 24.04 noble 0
assert_release debian 12 bookworm 1
assert_release ubuntu 22.04 jammy 1
printf '[OK] Debian/Ubuntu 版本契约测试通过（4 个 fixture）\n'
