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
ISO_TREE="$WORKSPACE/iso-tree"
readonly ISO_TREE
SOURCE_ISO="$WORKSPACE/lc300a-uefi.iso"
readonly SOURCE_ISO
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

assemble_iso() {
  local kernel
  local kernel_version
  local initrd
  local volume
  local report
  local checksum_file="$WORKSPACE/sha256sum.txt"
  local -a kernels

  mapfile -t kernels < <(find "$WORKSPACE/chroot/boot" -maxdepth 1 -type f -name 'vmlinuz-*' -print)
  [[ ${#kernels[@]} == 1 ]] || {
    print_status ERROR "预期 rootfs 包含 1 个内核，实际为 ${#kernels[@]}"
    return 1
  }
  kernel=${kernels[0]}
  kernel_version=${kernel##*/vmlinuz-}
  initrd="$WORKSPACE/chroot/boot/initrd.img-$kernel_version"
  [[ -f $initrd ]] || {
    print_status ERROR "内核缺少匹配的 initrd: $kernel_version"
    return 1
  }

  run_as_root rm -rf -- "$ISO_TREE"
  rm -f -- "$SOURCE_ISO"
  mkdir -p "$ISO_TREE/boot/grub" "$ISO_TREE/live"
  cp -- "$kernel" "$ISO_TREE/live/vmlinuz"
  cp -- "$initrd" "$ISO_TREE/live/initrd.img"
  cp -- "$WORKSPACE/lc300a-boot/grub.cfg" "$ISO_TREE/boot/grub/grub.cfg"
  run_as_root mksquashfs "$WORKSPACE/chroot" "$ISO_TREE/live/filesystem.squashfs" \
    -noappend -no-progress -comp xz
  run_as_root du -sx --block-size=1 "$WORKSPACE/chroot" \
    | cut -f1 >"$ISO_TREE/live/filesystem.size"
  (
    cd "$ISO_TREE"
    find . -type f -print0 \
      | LC_ALL=C sort -z \
      | xargs -0 sha256sum >"$checksum_file"
  )
  mv -- "$checksum_file" "$ISO_TREE/sha256sum.txt"

  volume=$(<"$WORKSPACE/lc300a-boot/volume-id")
  grub-mkrescue -o "$SOURCE_ISO" "$ISO_TREE" -- -volid "$volume"
  report=$(xorriso -indev "$SOURCE_ISO" -report_el_torito as_mkisofs 2>&1)
  grep -Eq -- '(^|[[:space:]])-e[[:space:]]' <<<"$report" || {
    print_status ERROR "ISO 缺少 UEFI El Torito 启动项"
    printf '%s\n' "$report" >&2
    return 1
  }
  print_status OK "GRUB UEFI ISO 已组装: $SOURCE_ISO"
}

build_iso() {
  local output_iso="$ARTIFACTS/LC300A-x86_64.iso"
  local package_manifest="$ARTIFACTS/package-manifest.txt"
  local build_log="$ARTIFACTS/live-build.log"

  build_rootfs 2>&1 | tee "$build_log"
  assemble_iso 2>&1 | tee -a "$build_log"
  cp -- "$SOURCE_ISO" "$output_iso"
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
