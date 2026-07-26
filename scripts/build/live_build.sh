#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
readonly PROJECT_ROOT
WORKSPACE="$PROJECT_ROOT/build/live-build/work"
readonly WORKSPACE
ARTIFACTS="$PROJECT_ROOT/build/artifacts"
readonly ARTIFACTS
# shellcheck source=/dev/null
source "$PROJECT_ROOT/scripts/bootstrap/lib.sh"

prepare() {
  "$PROJECT_ROOT/scripts/bootstrap/doctor.sh" --strict
  mkdir -p "$WORKSPACE" "$ARTIFACTS"
  python3 "$SCRIPT_DIR/configure_live.py" --workspace "$WORKSPACE"
}

build_rootfs() {
  prepare
  cd "$WORKSPACE"
  run_as_root lb bootstrap
  run_as_root lb chroot
  print_status OK "rootfs 已生成: $WORKSPACE/chroot"
}

build_iso() {
  local source_iso
  local output_iso="$ARTIFACTS/LC300A-x86_64.iso"
  local package_manifest="$ARTIFACTS/package-manifest.txt"
  local build_log="$ARTIFACTS/live-build.log"
  local -a images

  prepare
  cd "$WORKSPACE"
  run_as_root lb build 2>&1 | tee "$build_log"

  mapfile -t images < <(find "$WORKSPACE" -maxdepth 1 -type f -name '*.iso' -print)
  [[ ${#images[@]} == 1 ]] || {
    print_status ERROR "预期生成 1 个 ISO，实际为 ${#images[@]}"
    return 1
  }
  source_iso=${images[0]}
  cp -- "$source_iso" "$output_iso"
  (
    cd "$ARTIFACTS"
    sha256sum "${output_iso##*/}" >"${output_iso##*/}.sha256"
  )

  [[ -d $WORKSPACE/chroot ]] || {
    print_status ERROR "live-build chroot 不存在，无法生成软件包清单"
    return 1
  }
  # dpkg-query expands its own field syntax.
  # shellcheck disable=SC2016
  run_as_root chroot "$WORKSPACE/chroot" dpkg-query -W \
    -f='${binary:Package}\t${Version}\n' | LC_ALL=C sort >"$package_manifest"
  python3 "$SCRIPT_DIR/build_manifest.py" \
    --iso "$output_iso" \
    --packages "$package_manifest" \
    --output "$ARTIFACTS/build-manifest.json"
  print_status OK "ISO 已生成: $output_iso"
}

case ${1:-} in
  rootfs) build_rootfs ;;
  iso) build_iso ;;
  *)
    print_status ERROR "用法: $0 [rootfs|iso]"
    exit 2
    ;;
esac
