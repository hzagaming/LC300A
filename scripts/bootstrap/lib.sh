#!/usr/bin/env bash

set -Eeuo pipefail

# Arrays are consumed by scripts that source this file.
# shellcheck disable=SC2034
readonly LC300A_REQUIRED_COMMANDS=(bash git make python3)
# shellcheck disable=SC2034
readonly LC300A_LINUX_BUILD_COMMANDS=(
  debootstrap grub-mkstandalone jq lb mformat mkfs.vfat mksquashfs
  qemu-system-x86_64 rsync sha256sum xorriso
)
# shellcheck disable=SC2034
readonly LC300A_LINUX_BUILD_PACKAGES=(
  bash ca-certificates coreutils debootstrap dosfstools git grub-efi-amd64-bin
  grub-pc-bin jq live-build make mtools ovmf python3 qemu-system-x86 rsync
  shellcheck squashfs-tools xorriso
)

has_command() {
  command -v "$1" >/dev/null 2>&1
}

print_status() {
  local level=$1
  local message=$2
  printf '[%s] %s\n' "$level" "$message"
}

require_confirmation() {
  local prompt=$1

  if [[ ${LC300A_ASSUME_YES:-0} == 1 ]]; then
    return 0
  fi
  if [[ ! -t 0 ]]; then
    print_status ERROR "非交互环境需要设置 LC300A_ASSUME_YES=1 才能安装依赖"
    return 1
  fi

  local answer
  read -r -p "$prompt [y/N] " answer
  [[ $answer == y || $answer == Y ]]
}

run_as_root() {
  if [[ $EUID == 0 ]]; then
    "$@"
  elif has_command sudo; then
    sudo "$@"
  else
    print_status ERROR "需要 root 权限，但未找到 sudo"
    return 1
  fi
}

os_release_value() {
  local path=$1
  local field=$2

  [[ -r $path ]] || return 1
  (
    set +u
    # shellcheck source=/dev/null
    source "$path"
    printf '%s' "${!field:-}"
  )
}

is_supported_linux_release() {
  local path=${1:-/etc/os-release}
  local distro
  local version
  local codename

  distro=$(os_release_value "$path" ID) || return 1
  version=$(os_release_value "$path" VERSION_ID) || return 1
  codename=$(os_release_value "$path" VERSION_CODENAME) || return 1

  case "$distro:$version:$codename" in
    debian:13:*|debian:*:trixie|ubuntu:24.04:*) return 0 ;;
    *) return 1 ;;
  esac
}

require_supported_linux_release() {
  local expected_id=$1
  local path=${2:-/etc/os-release}
  local actual_id
  local version

  actual_id=$(os_release_value "$path" ID) || {
    print_status ERROR "无法读取 $path"
    return 1
  }
  version=$(os_release_value "$path" VERSION_ID) || true
  if [[ $actual_id != "$expected_id" ]]; then
    print_status ERROR "脚本要求 $expected_id，当前为 $actual_id"
    return 1
  fi
  if ! is_supported_linux_release "$path"; then
    print_status ERROR "不支持的 $actual_id 版本: ${version:-unknown}"
    return 1
  fi
  print_status OK "构建发行版: $actual_id ${version:-trixie}"
}

check_commands() {
  local missing=0
  local command_name

  for command_name in "$@"; do
    if has_command "$command_name"; then
      print_status OK "$command_name: $(command -v "$command_name")"
    else
      print_status MISSING "$command_name"
      missing=1
    fi
  done
  return "$missing"
}
