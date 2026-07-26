#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
readonly PROJECT_ROOT
readonly ISO_PATH="$PROJECT_ROOT/build/artifacts/LC300A-x86_64.iso"
readonly SERIAL_LOG="$PROJECT_ROOT/build/artifacts/boot-serial.log"
readonly OVMF_VARS_COPY="$PROJECT_ROOT/build/artifacts/OVMF_VARS.fd"
readonly BOOT_MARKER=LC300A_BOOT_OK
QEMU_PID=

find_ovmf() {
  local code
  local variables
  while IFS='|' read -r code variables; do
    [[ -r $code && -r $variables ]] && {
      printf '%s|%s\n' "$code" "$variables"
      return 0
    }
  done <<'EOF'
/usr/share/OVMF/OVMF_CODE_4M.fd|/usr/share/OVMF/OVMF_VARS_4M.fd
/usr/share/OVMF/OVMF_CODE.fd|/usr/share/OVMF/OVMF_VARS.fd
/usr/share/edk2/ovmf/OVMF_CODE.fd|/usr/share/edk2/ovmf/OVMF_VARS.fd
/opt/homebrew/share/qemu/edk2-x86_64-code.fd|/opt/homebrew/share/qemu/edk2-i386-vars.fd
/usr/local/share/qemu/edk2-x86_64-code.fd|/usr/local/share/qemu/edk2-i386-vars.fd
EOF
  return 1
}

qemu_arguments() {
  local code=$1
  local variables=$2
  local acceleration=tcg
  local cpu=max
  if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    acceleration=kvm
    cpu=host
  fi
  QEMU_ARGUMENTS=(
    -machine "q35,accel=$acceleration"
    -cpu "$cpu"
    -m 2048
    -smp 2
    -drive "if=pflash,format=raw,readonly=on,file=$code"
    -drive "if=pflash,format=raw,file=$variables"
    -cdrom "$ISO_PATH"
    -boot d
    -nic "user,model=virtio-net-pci"
    -device virtio-rng-pci
    -no-reboot
  )
}

require_inputs() {
  [[ -f $ISO_PATH ]] || {
    printf '[ERROR] ISO 不存在，请先运行 make iso\n' >&2
    exit 1
  }
  command -v qemu-system-x86_64 >/dev/null 2>&1 || {
    printf '[ERROR] 缺少 qemu-system-x86_64\n' >&2
    exit 1
  }
  OVMF_PAIR=$(find_ovmf) || {
    printf '[ERROR] 未找到 OVMF UEFI 固件\n' >&2
    exit 1
  }
  readonly OVMF_PAIR
  OVMF_CODE=${OVMF_PAIR%%|*}
  OVMF_VARS=${OVMF_PAIR#*|}
  readonly OVMF_CODE OVMF_VARS
  cp -- "$OVMF_VARS" "$OVMF_VARS_COPY"
  qemu_arguments "$OVMF_CODE" "$OVMF_VARS_COPY"
}

run_interactive() {
  require_inputs
  exec qemu-system-x86_64 "${QEMU_ARGUMENTS[@]}" -serial mon:stdio
}

test_boot() {
  local timeout_seconds=${BOOT_TIMEOUT_SECONDS:-180}
  local elapsed=0

  [[ $timeout_seconds =~ ^[0-9]+$ && $timeout_seconds -ge 30 && $timeout_seconds -le 600 ]] || {
    printf '[ERROR] BOOT_TIMEOUT_SECONDS 必须在 30 到 600 之间\n' >&2
    exit 2
  }
  require_inputs
  : >"$SERIAL_LOG"
  qemu-system-x86_64 "${QEMU_ARGUMENTS[@]}" \
    -display none \
    -monitor none \
    -serial "file:$SERIAL_LOG" &
  QEMU_PID=$!

  cleanup() {
    if [[ -n $QEMU_PID ]] && kill -0 "$QEMU_PID" >/dev/null 2>&1; then
      kill "$QEMU_PID" >/dev/null 2>&1 || true
      wait "$QEMU_PID" >/dev/null 2>&1 || true
    fi
  }
  trap cleanup EXIT INT TERM

  while ((elapsed < timeout_seconds)); do
    if grep -q "$BOOT_MARKER" "$SERIAL_LOG"; then
      printf '[OK] UEFI 启动测试通过，检测到 %s\n' "$BOOT_MARKER"
      return 0
    fi
    if ! kill -0 "$QEMU_PID" >/dev/null 2>&1; then
      printf '[ERROR] QEMU 在启动标记出现前退出\n' >&2
      tail -n 80 "$SERIAL_LOG" >&2
      return 1
    fi
    sleep 1
    ((elapsed += 1))
  done
  printf '[ERROR] %s 秒内未检测到启动标记\n' "$timeout_seconds" >&2
  tail -n 80 "$SERIAL_LOG" >&2
  return 1
}

case ${1:-} in
  run) run_interactive ;;
  test) test_boot ;;
  *)
    printf '[ERROR] 用法: %s [run|test]\n' "$0" >&2
    exit 2
    ;;
esac
