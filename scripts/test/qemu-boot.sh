#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
readonly PROJECT_ROOT
readonly ISO_PATH="$PROJECT_ROOT/build/artifacts/LC300A-x86_64.iso"
readonly SERIAL_LOG="$PROJECT_ROOT/build/artifacts/boot-serial.log"
readonly OVMF_VARS_COPY="$PROJECT_ROOT/build/artifacts/OVMF_VARS.fd"
readonly MONITOR_SOCKET="$PROJECT_ROOT/build/artifacts/qemu-monitor.sock"
readonly DESKTOP_SCREENSHOT="$PROJECT_ROOT/build/artifacts/desktop.ppm"
readonly FRAMEBUFFER_VALIDATION_LOG="$PROJECT_ROOT/build/artifacts/framebuffer-validation.log"
readonly BOOT_MARKER=LC300A_BOOT_OK
readonly DESKTOP_MARKER=LC300A_DESKTOP_OK
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
  local cpu=qemu64
  if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    acceleration=kvm
    cpu=host
  fi
  QEMU_ARGUMENTS=(
    -machine "q35,accel=$acceleration"
    -cpu "$cpu"
    -m 4096
    -smp 4
    -drive "if=pflash,format=raw,readonly=on,file=$code"
    -drive "if=pflash,format=raw,file=$variables"
    -cdrom "$ISO_PATH"
    -boot d
    -nic "user,model=virtio-net-pci"
    -device virtio-rng-pci
    -vga virtio
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

capture_framebuffer() {
  rm -f -- "$DESKTOP_SCREENSHOT"
  python3 - "$MONITOR_SOCKET" "$DESKTOP_SCREENSHOT" <<'PY'
import socket
import sys
import time
from pathlib import Path

monitor = sys.argv[1]
screenshot = Path(sys.argv[2])
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.settimeout(10)
    connection.connect(monitor)
    connection.recv(4096)
    connection.sendall(f"screendump {screenshot}\n".encode("utf-8"))
deadline = time.monotonic() + 10
while time.monotonic() < deadline:
    if screenshot.is_file() and screenshot.stat().st_size > 1024:
        break
    time.sleep(0.1)
else:
    raise SystemExit("QEMU 未生成桌面截图")
PY
  python3 "$PROJECT_ROOT/scripts/test/validate_framebuffer.py" "$DESKTOP_SCREENSHOT" \
    >"$FRAMEBUFFER_VALIDATION_LOG" 2>&1
}

test_desktop() {
  local timeout_seconds=${DESKTOP_TIMEOUT_SECONDS:-600}
  local framebuffer_timeout=${FRAMEBUFFER_TIMEOUT_SECONDS:-60}
  local elapsed=0
  local framebuffer_elapsed

  [[ $timeout_seconds =~ ^[0-9]+$ && $timeout_seconds -ge 60 && $timeout_seconds -le 1200 ]] || {
    printf '[ERROR] DESKTOP_TIMEOUT_SECONDS 必须在 60 到 1200 之间\n' >&2
    exit 2
  }
  [[ $framebuffer_timeout =~ ^[0-9]+$ && $framebuffer_timeout -ge 5 && $framebuffer_timeout -le 120 ]] || {
    printf '[ERROR] FRAMEBUFFER_TIMEOUT_SECONDS 必须在 5 到 120 之间\n' >&2
    exit 2
  }
  require_inputs
  rm -f -- "$MONITOR_SOCKET" "$DESKTOP_SCREENSHOT"
  : >"$SERIAL_LOG"
  qemu-system-x86_64 "${QEMU_ARGUMENTS[@]}" \
    -display none \
    -monitor "unix:$MONITOR_SOCKET,server=on,wait=off" \
    -serial "file:$SERIAL_LOG" &
  QEMU_PID=$!

  cleanup() {
    if [[ -n $QEMU_PID ]] && kill -0 "$QEMU_PID" >/dev/null 2>&1; then
      kill "$QEMU_PID" >/dev/null 2>&1 || true
      wait "$QEMU_PID" >/dev/null 2>&1 || true
    fi
    rm -f -- "$MONITOR_SOCKET"
  }
  trap cleanup EXIT INT TERM

  while ((elapsed < timeout_seconds)); do
    if grep -q "$DESKTOP_MARKER" "$SERIAL_LOG"; then
      framebuffer_elapsed=0
      while ((framebuffer_elapsed < framebuffer_timeout)); do
        if capture_framebuffer; then
          cat -- "$FRAMEBUFFER_VALIDATION_LOG"
          printf '[OK] UEFI 桌面测试通过，检测到 %s 并验证真实帧缓冲\n' "$DESKTOP_MARKER"
          return 0
        fi
        if ! kill -0 "$QEMU_PID" >/dev/null 2>&1; then
          printf '[ERROR] QEMU 在桌面绘制完成前退出\n' >&2
          return 1
        fi
        sleep 2
        ((framebuffer_elapsed += 2))
      done
      cat -- "$FRAMEBUFFER_VALIDATION_LOG" >&2
      printf '[ERROR] %s 秒内桌面未完成绘制\n' "$framebuffer_timeout" >&2
      return 1
    fi
    if ! kill -0 "$QEMU_PID" >/dev/null 2>&1; then
      printf '[ERROR] QEMU 在桌面就绪前退出\n' >&2
      tail -n 120 "$SERIAL_LOG" >&2
      return 1
    fi
    sleep 1
    ((elapsed += 1))
  done
  printf '[ERROR] %s 秒内未检测到桌面就绪标记\n' "$timeout_seconds" >&2
  tail -n 120 "$SERIAL_LOG" >&2
  return 1
}

case ${1:-} in
  run) run_interactive ;;
  test) test_boot ;;
  desktop) test_desktop ;;
  *)
    printf '[ERROR] 用法: %s [run|test|desktop]\n' "$0" >&2
    exit 2
    ;;
esac
