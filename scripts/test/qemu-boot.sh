#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
readonly PROJECT_ROOT
readonly ISO_PATH="${LC300A_ISO_PATH:-$PROJECT_ROOT/build/artifacts/LC300A-x86_64.iso}"
readonly SERIAL_LOG="$PROJECT_ROOT/build/artifacts/boot-serial.log"
readonly OVMF_VARS_COPY="$PROJECT_ROOT/build/artifacts/OVMF_VARS.fd"
readonly MONITOR_SOCKET="$PROJECT_ROOT/build/artifacts/qemu-monitor.sock"
readonly SERIAL_SOCKET="$PROJECT_ROOT/build/artifacts/qemu-serial.sock"
readonly SERIAL_COMMAND_PIPE="$PROJECT_ROOT/build/artifacts/qemu-serial.commands"
readonly DESKTOP_SCREENSHOT="$PROJECT_ROOT/build/artifacts/desktop.ppm"
readonly AUDIO_OUTPUT="$PROJECT_ROOT/build/artifacts/apps-audio.wav"
readonly FRAMEBUFFER_VALIDATION_LOG="$PROJECT_ROOT/build/artifacts/framebuffer-validation.log"
readonly BOOT_MARKER=LC300A_BOOT_OK
readonly CONSOLE_MARKER=LC300A_CONSOLE_OK
readonly DESKTOP_MARKER=LC300A_DESKTOP_OK
QEMU_PID=
SERIAL_BRIDGE_PID=
SERIAL_COMMAND_OPEN=0

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

select_console_entry() {
  python3 - "$MONITOR_SOCKET" <<'PY'
import socket
import sys
import time

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.settimeout(10)
    connection.connect(sys.argv[1])
    connection.recv(4096)
    for key in ("down", "ret"):
        connection.sendall(f"sendkey {key}\n".encode("utf-8"))
        time.sleep(0.5)
PY
}

test_console() {
  local timeout_seconds=${CONSOLE_TIMEOUT_SECONDS:-180}
  local elapsed=0
  local selected=0

  [[ $timeout_seconds =~ ^[0-9]+$ && $timeout_seconds -ge 30 && $timeout_seconds -le 600 ]] || {
    printf '[ERROR] CONSOLE_TIMEOUT_SECONDS 必须在 30 到 600 之间\n' >&2
    exit 2
  }
  require_inputs
  rm -f -- "$MONITOR_SOCKET"
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
    if ((selected == 0)) && grep -q '纯文字模式' "$SERIAL_LOG"; then
      select_console_entry
      selected=1
    fi
    if grep -q "$CONSOLE_MARKER" "$SERIAL_LOG"; then
      printf '[OK] UEFI 纯文字模式通过，检测到 %s\n' "$CONSOLE_MARKER"
      return 0
    fi
    if ! kill -0 "$QEMU_PID" >/dev/null 2>&1; then
      printf '[ERROR] QEMU 在纯文字模式标记出现前退出\n' >&2
      tail -n 120 "$SERIAL_LOG" >&2
      return 1
    fi
    sleep 1
    ((elapsed += 1))
  done
  printf '[ERROR] %s 秒内未检测到纯文字模式标记\n' "$timeout_seconds" >&2
  tail -n 120 "$SERIAL_LOG" >&2
  return 1
}

capture_framebuffer() {
  local screenshot=${1:-$DESKTOP_SCREENSHOT}
  if (($#)); then
    shift
  fi
  rm -f -- "$screenshot"
  python3 - "$MONITOR_SOCKET" "$screenshot" <<'PY'
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
  python3 "$PROJECT_ROOT/scripts/test/validate_framebuffer.py" "$screenshot" "$@" \
    >"$FRAMEBUFFER_VALIDATION_LOG" 2>&1
}

send_monitor_key() {
  python3 - "$MONITOR_SOCKET" "$1" <<'PY'
import socket
import sys
import time

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.settimeout(10)
    connection.connect(sys.argv[1])
    connection.recv(4096)
    connection.sendall(f"sendkey {sys.argv[2]}\n".encode("utf-8"))
    time.sleep(0.5)
PY
}

quit_qemu() {
  python3 - "$MONITOR_SOCKET" <<'PY'
import socket
import sys

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.settimeout(10)
    connection.connect(sys.argv[1])
    connection.recv(4096)
    connection.sendall(b"quit\n")
PY
  wait "$QEMU_PID" >/dev/null 2>&1 || true
  QEMU_PID=
}

start_serial_bridge() {
  rm -f -- "$SERIAL_COMMAND_PIPE"
  mkfifo "$SERIAL_COMMAND_PIPE"
  exec 9<>"$SERIAL_COMMAND_PIPE"
  SERIAL_COMMAND_OPEN=1
  python3 "$PROJECT_ROOT/scripts/test/serial-console.py" \
    "$SERIAL_SOCKET" "$SERIAL_LOG" "$SERIAL_COMMAND_PIPE" &
  SERIAL_BRIDGE_PID=$!
}

stop_serial_bridge() {
  if ((SERIAL_COMMAND_OPEN)); then
    exec 9>&-
    SERIAL_COMMAND_OPEN=0
  fi
  if [[ -n $SERIAL_BRIDGE_PID ]] && kill -0 "$SERIAL_BRIDGE_PID" >/dev/null 2>&1; then
    kill "$SERIAL_BRIDGE_PID" >/dev/null 2>&1 || true
    wait "$SERIAL_BRIDGE_PID" >/dev/null 2>&1 || true
  fi
  SERIAL_BRIDGE_PID=
}

send_serial_line() {
  printf '%s\r' "$1" >&9
}

wait_for_serial() {
  local marker=$1
  local timeout_seconds=$2
  local elapsed=0
  while ((elapsed < timeout_seconds)); do
    grep -Fq -- "$marker" "$SERIAL_LOG" && return 0
    if ! kill -0 "$QEMU_PID" >/dev/null 2>&1; then
      printf '[ERROR] QEMU 在等待串口内容时退出: %s\n' "$marker" >&2
      return 1
    fi
    if [[ -n $SERIAL_BRIDGE_PID ]] && ! kill -0 "$SERIAL_BRIDGE_PID" >/dev/null 2>&1; then
      printf '[ERROR] 串口桥在等待内容时退出: %s\n' "$marker" >&2
      return 1
    fi
    sleep 1
    ((elapsed += 1))
  done
  printf '[ERROR] %s 秒内未检测到串口内容: %s\n' "$timeout_seconds" "$marker" >&2
  return 1
}

run_guest_command() {
  local command=$1
  local marker=$2
  local timeout_seconds=$3
  send_serial_line "$command; lc300a_status=\$?; printf '\\n$marker:%s\\n' \"\$lc300a_status\""
  wait_for_serial "$marker:" "$timeout_seconds" || return 1
  grep -Fq -- "$marker:0" "$SERIAL_LOG" || {
    printf '[ERROR] 访客命令失败: %s\n' "$marker" >&2
    return 1
  }
}

wait_for_framebuffer() {
  local screenshot=$1
  local timeout_seconds=$2
  local elapsed=0
  shift 2
  while ((elapsed < timeout_seconds)); do
    if capture_framebuffer "$screenshot" "$@"; then
      cat -- "$FRAMEBUFFER_VALIDATION_LOG"
      return 0
    fi
    if ! kill -0 "$QEMU_PID" >/dev/null 2>&1; then
      printf '[ERROR] QEMU 在图形验收完成前退出\n' >&2
      return 1
    fi
    sleep 2
    ((elapsed += 2))
  done
  cat -- "$FRAMEBUFFER_VALIDATION_LOG" >&2
  return 1
}

test_desktop() {
  local timeout_seconds=${DESKTOP_TIMEOUT_SECONDS:-600}
  local framebuffer_timeout=${FRAMEBUFFER_TIMEOUT_SECONDS:-120}
  local stability_seconds=${FRAMEBUFFER_STABILITY_SECONDS:-15}
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
  [[ $stability_seconds =~ ^[0-9]+$ && $stability_seconds -ge 5 && $stability_seconds -le 60 ]] || {
    printf '[ERROR] FRAMEBUFFER_STABILITY_SECONDS 必须在 5 到 60 之间\n' >&2
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
      sleep "$stability_seconds"
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

test_apps() {
  local desktop_timeout=${DESKTOP_TIMEOUT_SECONDS:-600}
  local launch_timeout=${APP_LAUNCH_TIMEOUT_SECONDS:-120}
  local restore_timeout=${APP_RESTORE_TIMEOUT_SECONDS:-60}
  local settle_seconds=${APP_SETTLE_SECONDS:-30}
  local stability_seconds=${FRAMEBUFFER_STABILITY_SECONDS:-15}

  [[ $desktop_timeout =~ ^[0-9]+$ && $desktop_timeout -ge 60 && $desktop_timeout -le 1200 ]] || {
    printf '[ERROR] DESKTOP_TIMEOUT_SECONDS 必须在 60 到 1200 之间\n' >&2
    exit 2
  }
  [[ $launch_timeout =~ ^[0-9]+$ && $launch_timeout -ge 10 && $launch_timeout -le 240 ]] || {
    printf '[ERROR] APP_LAUNCH_TIMEOUT_SECONDS 必须在 10 到 240 之间\n' >&2
    exit 2
  }
  [[ $restore_timeout =~ ^[0-9]+$ && $restore_timeout -ge 10 && $restore_timeout -le 120 ]] || {
    printf '[ERROR] APP_RESTORE_TIMEOUT_SECONDS 必须在 10 到 120 之间\n' >&2
    exit 2
  }
  [[ $settle_seconds =~ ^[0-9]+$ && $settle_seconds -ge 10 && $settle_seconds -le 120 ]] || {
    printf '[ERROR] APP_SETTLE_SECONDS 必须在 10 到 120 之间\n' >&2
    exit 2
  }
  [[ $stability_seconds =~ ^[0-9]+$ && $stability_seconds -ge 5 && $stability_seconds -le 60 ]] || {
    printf '[ERROR] FRAMEBUFFER_STABILITY_SECONDS 必须在 5 到 60 之间\n' >&2
    exit 2
  }

  require_inputs
  rm -f -- "$MONITOR_SOCKET" "$SERIAL_SOCKET" "$SERIAL_COMMAND_PIPE" \
    "$AUDIO_OUTPUT"
  : >"$SERIAL_LOG"
  qemu-system-x86_64 "${QEMU_ARGUMENTS[@]}" \
    -display none \
    -monitor "unix:$MONITOR_SOCKET,server=on,wait=off" \
    -serial "unix:$SERIAL_SOCKET,server=on,wait=off" \
    -audiodev "wav,id=audio0,path=$AUDIO_OUTPUT" \
    -device ich9-intel-hda \
    -device hda-output,audiodev=audio0 &
  QEMU_PID=$!
  start_serial_bridge

  cleanup() {
    stop_serial_bridge
    if [[ -n $QEMU_PID ]] && kill -0 "$QEMU_PID" >/dev/null 2>&1; then
      kill "$QEMU_PID" >/dev/null 2>&1 || true
      wait "$QEMU_PID" >/dev/null 2>&1 || true
    fi
    rm -f -- "$MONITOR_SOCKET" "$SERIAL_SOCKET" "$SERIAL_COMMAND_PIPE"
  }
  trap cleanup EXIT INT TERM

  wait_for_serial "$DESKTOP_MARKER" "$desktop_timeout" || {
    tail -n 120 "$SERIAL_LOG" >&2
    return 1
  }
  sleep "$stability_seconds"
  send_serial_line ""
  wait_for_serial "login:" 30 || return 1
  send_serial_line "lc300a-live"
  wait_for_serial "Password:" 30 || return 1
  send_serial_line "live"
  sleep 2
  send_serial_line "stty -echo"
  sleep 1
  run_guest_command \
    "export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus" \
    LC300A_GUEST_SESSION 30 || return 1

  test_application() {
    local name=$1
    local unit=$2
    local command=$3
    local baseline="$PROJECT_ROOT/build/artifacts/apps-$name-baseline.ppm"
    local screenshot="$PROJECT_ROOT/build/artifacts/apps-$name.ppm"
    local restored="$PROJECT_ROOT/build/artifacts/apps-$name-restored.ppm"
    local firefox_page="$PROJECT_ROOT/build/artifacts/apps-firefox-page.ppm"

    send_monitor_key shift
    wait_for_framebuffer "$baseline" 30 || return 1
    run_guest_command "$command" "LC300A_${name}_START" 30 || return 1
    run_guest_command \
      "for attempt in \$(seq 1 $launch_timeout); do systemctl --user is-active --quiet '$unit' && break; sleep 1; done; systemctl --user is-active --quiet '$unit'" \
      "LC300A_${name}_ACTIVE" "$launch_timeout" || return 1
    sleep "$settle_seconds"
    send_monitor_key shift
    if [[ $name == discover ]]; then
      wait_for_framebuffer "$screenshot" "$launch_timeout" \
        --reference "$baseline" --minimum-change-ratio 0.15 \
        --minimum-content-colors 32 || return 1
    else
      wait_for_framebuffer "$screenshot" "$launch_timeout" \
        --reference "$baseline" --minimum-change-ratio 0.15 || return 1
    fi
    if [[ $name == firefox ]]; then
      run_guest_command \
        "/usr/bin/python3 -c \"import urllib.request; response = urllib.request.urlopen('https://example.com', timeout=30); content = response.read(); assert response.status == 200 and b'Example Domain' in content\"" \
        LC300A_FIREFOX_NETWORK 45 || return 1
      run_guest_command \
        "/usr/bin/systemd-run --user --wait --collect --quiet -- /usr/bin/firefox-esr --new-tab https://example.com" \
        LC300A_FIREFOX_NAVIGATE 30 || return 1
      wait_for_framebuffer "$firefox_page" "$launch_timeout" \
        --reference "$screenshot" --minimum-change-ratio 0.01 \
        --minimum-content-dark-ratio 0.002 || return 1
    fi
    run_guest_command \
      "systemctl --user stop '$unit'; ! systemctl --user is-active --quiet '$unit'" \
      "LC300A_${name}_STOP" 30 || return 1
    wait_for_framebuffer "$restored" "$restore_timeout" \
      --reference "$baseline" --maximum-change-ratio 0.05 || return 1
    printf '[OK] 图形应用已保持运行并绘制窗口: %s\n' "$name"
  }

  test_application konsole lc300a-e2e-konsole.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-konsole --collect -- /usr/bin/konsole --nofork -e /bin/sh -c 'printf LC300A_TERMINAL_OK; exec sleep 300'" || return 1
  test_application firefox lc300a-e2e-firefox.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-firefox --collect -- /usr/bin/firefox-esr --new-window https://example.com" || return 1
  test_application discover lc300a-e2e-discover.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-discover --collect -- /usr/local/bin/plasma-discover" || return 1

  python3 "$PROJECT_ROOT/scripts/test/validate_audio_output.py" "$AUDIO_OUTPUT" \
    --maximum-active-duration 2.5 || return 1
  printf '[OK] 自动会话音效有效且未检测到自动 BGM\n'
  run_guest_command \
    "/usr/bin/pw-play --volume=0.45 /usr/share/sounds/luochuan-flow/stereo/desktop-login.wav" \
    LC300A_AUDIO_PLAYBACK 60 || return 1
  stop_serial_bridge
  quit_qemu
  python3 "$PROJECT_ROOT/scripts/test/validate_audio_output.py" "$AUDIO_OUTPUT" || return 1
  printf '[OK] Konsole、Firefox、Discover 与音频图形交互测试通过\n'
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  case ${1:-} in
    run) run_interactive ;;
    test) test_boot ;;
    console) test_console ;;
    desktop) test_desktop ;;
    apps) test_apps ;;
    *)
      printf '[ERROR] 用法: %s [run|test|console|desktop|apps]\n' "$0" >&2
      exit 2
      ;;
  esac
fi
