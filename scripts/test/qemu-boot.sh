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
readonly QEMU_MEMORY_MIB=${LC300A_QEMU_MEMORY_MIB:-2048}
readonly QEMU_CPUS=${LC300A_QEMU_CPUS:-6}
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
  local acceleration='tcg,thread=multi,tb-size=256'
  local cpu=qemu64
  if [[ -r /dev/kvm && -w /dev/kvm ]]; then
    acceleration=kvm
    cpu=host
  fi
  QEMU_ARGUMENTS=(
    -machine q35
    -accel "$acceleration"
    -cpu "$cpu"
    -m "$QEMU_MEMORY_MIB"
    -smp "$QEMU_CPUS"
    -drive "if=pflash,format=raw,readonly=on,file=$code"
    -drive "if=pflash,format=raw,file=$variables"
    -cdrom "$ISO_PATH"
    -boot d
    -nic "user,model=virtio-net-pci"
    -device virtio-rng-pci
    -vga none
    -device "virtio-vga,xres=1280,yres=800"
    -no-reboot
  )
}

validate_qemu_resources() {
  [[ $QEMU_MEMORY_MIB =~ ^[0-9]+$ && $QEMU_MEMORY_MIB -ge 1024 && $QEMU_MEMORY_MIB -le 16384 ]] || {
    printf '[ERROR] LC300A_QEMU_MEMORY_MIB 必须在 1024 到 16384 之间\n' >&2
    exit 2
  }
  [[ $QEMU_CPUS =~ ^[0-9]+$ && $QEMU_CPUS -ge 1 && $QEMU_CPUS -le 32 ]] || {
    printf '[ERROR] LC300A_QEMU_CPUS 必须在 1 到 32 之间\n' >&2
    exit 2
  }
}

require_inputs() {
  validate_qemu_resources
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
  local app_filter=${LC300A_APP_FILTER:-}

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
  case $app_filter in
    '' | konsole | dolphin | kate | kcalc | ark | gwenview | kamoso | systemsettings | welcome | firefox | discover) ;;
    *)
      printf '[ERROR] LC300A_APP_FILTER 不是受支持的应用: %s\n' "$app_filter" >&2
      exit 2
      ;;
  esac

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
    "export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus XDG_CURRENT_DESKTOP=KDE KDE_FULL_SESSION=true KDE_SESSION_VERSION=6" \
    LC300A_GUEST_SESSION 30 || return 1
  run_guest_command \
    "cli_temp=\$(mktemp -d); (curl --version >/dev/null && wget --version >/dev/null && htop --version >/dev/null && printf '%s\n' '{\"ok\":true}' > \"\$cli_temp/source.json\" && git init -q \"\$cli_temp/repo\" && test \"\$(git -C \"\$cli_temp/repo\" rev-parse --is-inside-work-tree)\" = true && jq -e .ok \"\$cli_temp/source.json\" >/dev/null && printf LC300A_TOOL_OK | rg -q TOOL_OK && rsync -a \"\$cli_temp/source.json\" \"\$cli_temp/copy.json\" && cmp \"\$cli_temp/source.json\" \"\$cli_temp/copy.json\" && tree --noreport \"\$cli_temp\" | rg -q source.json && zip -jq \"\$cli_temp/archive.zip\" \"\$cli_temp/source.json\" && test \"\$(unzip -p \"\$cli_temp/archive.zip\" source.json | jq -r .ok)\" = true && lsof -p \$\$ | rg -q '^COMMAND'); cli_status=\$?; rm -rf -- \"\$cli_temp\"; test \"\$cli_status\" -eq 0" \
    LC300A_CLI_TOOLS 60 || return 1
  run_guest_command \
    "systemctl is-active --quiet systemd-zram-setup@zram0.service && grep -q '^/dev/zram0 ' /proc/swaps && test \"\$(cat /sys/block/zram0/disksize)\" -gt 0" \
    LC300A_ZRAM_ACTIVE 30 || return 1
  run_guest_command \
    "grep -Fqx 'Indexing-Enabled=false' /etc/xdg/baloofilerc && ! pgrep -x baloo_file" \
    LC300A_BALOO_DISABLED 30 || return 1

  diagnose_application() {
    local name=$1
    local unit=$2
    run_guest_command \
      "systemctl --user status '$unit' --no-pager || true; sudo journalctl _SYSTEMD_USER_UNIT='$unit' -n 120 --no-pager || true; test -f \"\$HOME/.cache/lc300a-e2e-$name.log\" && cat \"\$HOME/.cache/lc300a-e2e-$name.log\" || true; pgrep -a -f '/usr/bin/$name' || true; true" \
      "LC300A_${name}_DIAGNOSTICS" 30 || true
  }

  test_application() {
    local name=$1
    local unit=$2
    local command=$3
    local baseline="$PROJECT_ROOT/build/artifacts/apps-$name-baseline.ppm"
    local screenshot="$PROJECT_ROOT/build/artifacts/apps-$name.ppm"
    local restored="$PROJECT_ROOT/build/artifacts/apps-$name-restored.ppm"

    [[ -z $app_filter || $name == "$app_filter" ]] || return 0

    if [[ $name == firefox ]]; then
      screenshot="$PROJECT_ROOT/build/artifacts/apps-firefox-page.ppm"
    fi

    send_monitor_key shift
    wait_for_framebuffer "$baseline" 30 || return 1
    if [[ $name == firefox ]]; then
      run_guest_command \
        "/usr/bin/python3 -c \"import urllib.request; response = urllib.request.urlopen('https://example.com', timeout=30); content = response.read(); assert response.status == 200 and b'Example Domain' in content\"" \
        LC300A_FIREFOX_NETWORK 45 || return 1
    fi
    run_guest_command "$command" "LC300A_${name}_START" 30 || return 1
    run_guest_command \
      "for attempt in \$(seq 1 $launch_timeout); do systemctl --user is-active --quiet '$unit' && break; sleep 1; done; systemctl --user is-active --quiet '$unit'" \
      "LC300A_${name}_ACTIVE" "$launch_timeout" || return 1
    sleep "$settle_seconds"
    send_monitor_key shift
    if [[ $name == discover || $name == welcome ]]; then
      if ! wait_for_framebuffer "$screenshot" "$launch_timeout" \
        --reference "$baseline" --minimum-change-ratio 0.15 \
        --minimum-content-colors 32 \
        --minimum-content-chroma-ratio 0.02; then
        diagnose_application "$name" "$unit"
        if [[ $name == discover ]]; then
          run_guest_command \
            "sudo journalctl -u packagekit.service -n 120 --no-pager || true; /usr/bin/appstreamcli status || true; find /var/lib/swcatalog -maxdepth 3 -type f -print || true; /usr/bin/python3 -c \"import urllib.request; assert urllib.request.urlopen('http://mirrors.tuna.tsinghua.edu.cn/debian/dists/trixie/InRelease', timeout=30).status == 200\" || true" \
            LC300A_DISCOVER_DIAGNOSTICS 60 || true
        fi
        return 1
      fi
    elif [[ $name == firefox ]]; then
      if ! wait_for_framebuffer "$screenshot" "$launch_timeout" \
        --reference "$baseline" --minimum-change-ratio 0.15 \
        --minimum-content-dark-ratio 0.002; then
        diagnose_application "$name" "$unit"
        return 1
      fi
    else
      if ! wait_for_framebuffer "$screenshot" "$launch_timeout" \
        --reference "$baseline" --minimum-change-ratio 0.15; then
        diagnose_application "$name" "$unit"
        return 1
      fi
    fi
    if [[ $name == welcome ]]; then
      local previous=$screenshot
      local step_screenshot
      local step
      for step in 2 3 4; do
        send_monitor_key spc
        sleep 3
        step_screenshot="$PROJECT_ROOT/build/artifacts/apps-welcome-step$step.ppm"
        wait_for_framebuffer "$step_screenshot" "$launch_timeout" \
          --reference "$previous" --minimum-change-ratio 0.02 \
          --minimum-content-colors 32 \
          --minimum-content-chroma-ratio 0.01 || return 1
        previous=$step_screenshot
      done
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
  test_application dolphin lc300a-e2e-dolphin.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-dolphin --collect -- /usr/bin/dolphin --new-window /home/lc300a-live" || return 1
  test_application kate lc300a-e2e-kate.service \
    "/usr/bin/mkdir -p \"\$HOME/.cache\" && /usr/bin/systemd-run --user --unit=lc300a-e2e-kate --collect -- /bin/sh -c 'exec /usr/bin/kate -b > \"\$HOME/.cache/lc300a-e2e-kate.log\" 2>&1'" || return 1
  test_application kcalc lc300a-e2e-kcalc.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-kcalc --collect -- /usr/bin/kcalc" || return 1
  test_application ark lc300a-e2e-ark.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-ark --collect -- /usr/bin/ark" || return 1
  test_application gwenview lc300a-e2e-gwenview.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-gwenview --collect -- /usr/bin/gwenview" || return 1
  test_application kamoso lc300a-e2e-kamoso.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-kamoso --collect -- /usr/bin/kamoso" || return 1
  test_application systemsettings lc300a-e2e-systemsettings.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-systemsettings --collect -- /usr/bin/systemsettings" || return 1
  test_application welcome lc300a-e2e-welcome.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-welcome --collect -- /usr/local/bin/lc300a-welcome" || return 1
  if [[ -z $app_filter || $app_filter == welcome ]]; then
    run_guest_command \
      "test \"\$(xdg-mime query default x-scheme-handler/lc300a-action)\" = lc300a-welcome-action.desktop && rm -f \"\$HOME/.config/lc300a/welcome-complete\" && /usr/bin/systemd-run --user --unit=lc300a-e2e-welcome-action --collect --wait -- /usr/bin/xdg-open lc300a-action:finish && for attempt in \$(seq 1 30); do test -f \"\$HOME/.config/lc300a/welcome-complete\" && break; sleep 1; done; test \"\$(cat \"\$HOME/.config/lc300a/welcome-complete\")\" = completed=true && test \"\$(stat -c %a \"\$HOME/.config/lc300a/welcome-complete\")\" = 600" \
      LC300A_WELCOME_ACTION 40 || return 1
  fi
  test_application firefox lc300a-e2e-firefox.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-firefox --collect -- /usr/bin/firefox-esr --new-window https://example.com" || return 1
  test_application discover lc300a-e2e-discover.service \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-discover --collect -- /usr/local/bin/plasma-discover" || return 1

  if [[ -n $app_filter ]]; then
    stop_serial_bridge
    quit_qemu
    printf '[OK] 定向应用测试通过: %s\n' "$app_filter"
    return 0
  fi

  python3 "$PROJECT_ROOT/scripts/test/validate_audio_output.py" "$AUDIO_OUTPUT" \
    --maximum-active-duration 2.25 || return 1
  printf '[OK] 自动会话音效有效且未检测到自动 BGM\n'
  run_guest_command \
    "/usr/bin/pw-play --volume=0.45 /usr/share/sounds/luochuan-flow/preview/ambient-preview.wav" \
    LC300A_AUDIO_PLAYBACK 60 || return 1
  stop_serial_bridge
  quit_qemu
  python3 "$PROJECT_ROOT/scripts/test/validate_audio_output.py" "$AUDIO_OUTPUT" \
    --minimum-active-duration 2.5 || return 1
  printf '[OK] 基础工具、低内存策略、常用图形应用与音频交互测试通过\n'
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
