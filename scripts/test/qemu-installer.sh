#!/usr/bin/env bash

set -Eeuo pipefail

INSTALLER_SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly INSTALLER_SCRIPT_DIR
# shellcheck source=qemu-boot.sh disable=SC1091
source "$INSTALLER_SCRIPT_DIR/qemu-boot.sh"

readonly INSTALLER_DISK="$PROJECT_ROOT/build/artifacts/installer-test.qcow2"
readonly INSTALLER_BASELINE="$PROJECT_ROOT/build/artifacts/installer-baseline.ppm"
readonly INSTALLER_SCREENSHOT="$PROJECT_ROOT/build/artifacts/installer-welcome.ppm"
readonly INSTALLED_LOGIN_SCREENSHOT="$PROJECT_ROOT/build/artifacts/installed-login.ppm"
readonly INSTALLED_DESKTOP_SCREENSHOT="$PROJECT_ROOT/build/artifacts/installed-desktop.ppm"
readonly INSTALLER_TEST_USER=lc300a-test
readonly INSTALLER_TEST_PASSWORD=RiverStone-300

validate_installation_timeouts() {
  local install_timeout=${INSTALLER_TIMEOUT_SECONDS:-3600}
  local boot_timeout=${INSTALLED_BOOT_TIMEOUT_SECONDS:-900}
  [[ $install_timeout =~ ^[0-9]+$ && $install_timeout -ge 300 && $install_timeout -le 7200 ]] || {
    printf '[ERROR] INSTALLER_TIMEOUT_SECONDS 必须在 300 到 7200 之间\n' >&2
    return 2
  }
  [[ $boot_timeout =~ ^[0-9]+$ && $boot_timeout -ge 120 && $boot_timeout -le 1800 ]] || {
    printf '[ERROR] INSTALLED_BOOT_TIMEOUT_SECONDS 必须在 120 到 1800 之间\n' >&2
    return 2
  }
}

disable_installer_network() {
  local index
  for ((index = 0; index < ${#QEMU_ARGUMENTS[@]}; index++)); do
    if [[ ${QEMU_ARGUMENTS[index]} == -nic ]]; then
      QEMU_ARGUMENTS[index+1]=none
      return 0
    fi
  done
  printf '[ERROR] QEMU 参数缺少可禁用的网络设备\n' >&2
  return 1
}

type_monitor_text() {
  python3 - "$MONITOR_SOCKET" "$1" <<'PY'
import socket
import sys
import time

mapping = {"-": "minus", " ": "spc"}
with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
    connection.settimeout(10)
    connection.connect(sys.argv[1])
    connection.recv(4096)
    for character in sys.argv[2]:
        key = mapping.get(character, character.lower())
        if character.isupper():
            key = f"shift-{key}"
        connection.sendall(f"sendkey {key}\n".encode("ascii"))
        time.sleep(0.12)
PY
}

select_erase_disk() {
  send_monitor_key tab
  send_monitor_key tab
  send_monitor_key tab
  send_monitor_key spc
}

walk_installer_pages() {
  local previous=$INSTALLER_SCREENSHOT
  local screenshot
  local page
  for page in locale keyboard partition; do
    send_monitor_key alt-n
    sleep 8
    screenshot="$PROJECT_ROOT/build/artifacts/installer-$page.ppm"
    wait_for_framebuffer "$screenshot" 60 \
      --reference "$previous" --minimum-change-ratio 0.01
    previous=$screenshot
  done
  printf '[OK] Calamares 已通过欢迎、地区、键盘并进入分区页\n'
}

complete_installer() {
  local install_timeout=${INSTALLER_TIMEOUT_SECONDS:-3600}
  local partition_screenshot="$PROJECT_ROOT/build/artifacts/installer-partition.ppm"
  local partition_selected_screenshot="$PROJECT_ROOT/build/artifacts/installer-partition-choice.ppm"
  local users_screenshot="$PROJECT_ROOT/build/artifacts/installer-users.ppm"
  local summary_screenshot="$PROJECT_ROOT/build/artifacts/installer-summary.ppm"
  local installing_screenshot="$PROJECT_ROOT/build/artifacts/installer-installing.ppm"
  local finished_screenshot="$PROJECT_ROOT/build/artifacts/installer-finished.ppm"

  for page in locale keyboard partition; do
    send_monitor_key alt-n
    sleep 8
  done
  wait_for_framebuffer "$partition_screenshot" 60
  select_erase_disk
  wait_for_framebuffer "$partition_selected_screenshot" 60 \
    --reference "$partition_screenshot" --minimum-change-ratio 0.01
  send_monitor_key alt-n
  wait_for_framebuffer "$users_screenshot" 60 \
    --reference "$partition_selected_screenshot" --minimum-change-ratio 0.04

  type_monitor_text "LC300A Test User"
  send_monitor_key tab
  type_monitor_text "$INSTALLER_TEST_USER"
  send_monitor_key tab
  type_monitor_text "$INSTALLER_TEST_USER"
  send_monitor_key tab
  type_monitor_text "$INSTALLER_TEST_PASSWORD"
  send_monitor_key tab
  type_monitor_text "$INSTALLER_TEST_PASSWORD"
  send_monitor_key alt-n
  wait_for_framebuffer "$summary_screenshot" 60 \
    --reference "$users_screenshot" --minimum-change-ratio 0.04
  send_monitor_key alt-i
  sleep 5
  send_monitor_key ret
  wait_for_framebuffer "$installing_screenshot" 60 \
    --reference "$summary_screenshot" --minimum-change-ratio 0.04

  wait_for_serial LC300A_INSTALL_OK "$install_timeout" || {
    run_guest_command \
      "sudo journalctl _SYSTEMD_USER_UNIT=lc300a-e2e-installer.service -n 160 --no-pager || true" \
      LC300A_INSTALLER_FAILURE_LOG 30 || true
    return 1
  }
  wait_for_framebuffer "$finished_screenshot" 120 \
    --reference "$installing_screenshot" --minimum-change-ratio 0.04
  printf '[OK] Calamares 已完成虚拟硬盘安装并绘制完成页\n'
}

installed_qemu_arguments() {
  local skip=0
  local argument
  INSTALLED_QEMU_ARGUMENTS=()
  for argument in "${QEMU_ARGUMENTS[@]}"; do
    if ((skip)); then
      skip=0
      continue
    fi
    case $argument in
      -cdrom|-boot)
        skip=1
        ;;
      *)
        INSTALLED_QEMU_ARGUMENTS+=("$argument")
        ;;
    esac
  done
}

boot_installed_system() {
  local boot_timeout=${INSTALLED_BOOT_TIMEOUT_SECONDS:-900}

  stop_serial_bridge
  quit_qemu
  rm -f -- "$MONITOR_SOCKET" "$SERIAL_SOCKET" "$SERIAL_COMMAND_PIPE" \
    "$INSTALLED_LOGIN_SCREENSHOT" "$INSTALLED_DESKTOP_SCREENSHOT"
  : >"$SERIAL_LOG"
  installed_qemu_arguments
  qemu-system-x86_64 "${INSTALLED_QEMU_ARGUMENTS[@]}" \
    -drive "if=virtio,format=qcow2,file=$INSTALLER_DISK" \
    -display none \
    -monitor "unix:$MONITOR_SOCKET,server=on,wait=off" \
    -serial "unix:$SERIAL_SOCKET,server=on,wait=off" &
  QEMU_PID=$!
  start_serial_bridge

  wait_for_serial "login:" "$boot_timeout"
  send_serial_line "$INSTALLER_TEST_USER"
  wait_for_serial "Password:" 60
  send_serial_line "$INSTALLER_TEST_PASSWORD"
  sleep 3
  send_serial_line "stty -echo"
  sleep 1
  run_guest_command \
    "test \"\$(. /etc/os-release; printf '%s' \"\$ID\")\" = lc300a && test -x /usr/sbin/hwclock && test \"\$(findmnt -n -o FSTYPE /)\" = ext4 && findmnt -n -o FSTYPE /boot/efi | grep -Eq '^(vfat|fat)' && ! dpkg-query -W calamares >/dev/null 2>&1 && ! dpkg-query -W live-boot >/dev/null 2>&1 && test ! -e /usr/share/applications/lc300a-installer.desktop && test \"\$(systemctl get-default)\" = graphical.target" \
    LC300A_INSTALLED_SYSTEM_OK 120

  wait_for_framebuffer "$INSTALLED_LOGIN_SCREENSHOT" 120
  type_monitor_text "$INSTALLER_TEST_PASSWORD"
  send_monitor_key ret
  run_guest_command \
    "found=; for attempt in \$(seq 1 300); do if pgrep -u \$(id -u) -x plasmashell >/dev/null; then found=1; break; fi; sleep 1; done; test \"\$found\" = 1" \
    LC300A_INSTALLED_DESKTOP_OK 320
  sleep 20
  wait_for_framebuffer "$INSTALLED_DESKTOP_SCREENSHOT" 120 \
    --reference "$INSTALLED_LOGIN_SCREENSHOT" --minimum-change-ratio 0.15
  printf '[OK] 已移除 ISO 并通过 SDDM 登录安装后的 Plasma 桌面\n'
}

login_live_console() {
  send_serial_line ""
  wait_for_serial "login:" 30
  send_serial_line "lc300a-live"
  wait_for_serial "Password:" 30
  send_serial_line "live"
  sleep 2
  send_serial_line "stty -echo"
  sleep 1
  run_guest_command \
    "export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus" \
    LC300A_INSTALLER_SESSION 30
}

launch_installer() {
  run_guest_command \
    "sudo -E systemd-inhibit --what=idle:sleep --who='LC300A Installer' --why='LC300A installation test' --mode=block true" \
    LC300A_INSTALLER_INHIBIT 30
  run_guest_command \
    "/usr/bin/systemd-run --user --unit=lc300a-e2e-installer --collect -- /usr/local/bin/lc300a-installer -d" \
    LC300A_INSTALLER_START 30
  run_guest_command \
    "found=; for attempt in \$(seq 1 120); do if pgrep -x calamares >/dev/null; then found=1; break; fi; sleep 1; done; test \"\$found\" = 1" \
    LC300A_INSTALLER_ACTIVE 130
  run_guest_command \
    "found=; for attempt in \$(seq 1 240); do if sudo journalctl _SYSTEMD_USER_UNIT=lc300a-e2e-installer.service --no-pager | grep -Fq 'ViewModule \"finished@finished\" loading complete.'; then found=1; break; fi; sleep 1; done; test \"\$found\" = 1" \
    LC300A_INSTALLER_READY 250
}

wait_for_installer_stability() {
  local checksum
  local elapsed=0
  local previous=
  local stable_frames=0

  while ((elapsed < 120)); do
    if capture_framebuffer "$INSTALLER_SCREENSHOT"; then
      checksum=$(cksum <"$INSTALLER_SCREENSHOT")
      if [[ $checksum == "$previous" ]]; then
        ((stable_frames += 1))
        ((stable_frames >= 2)) && {
          printf '[OK] Calamares 欢迎页已完成加载并保持稳定\n'
          return 0
        }
      else
        previous=$checksum
        stable_frames=0
      fi
    fi
    kill -0 "$QEMU_PID" >/dev/null 2>&1 || return 1
    sleep 2
    ((elapsed += 2))
  done
  printf '[ERROR] Calamares 欢迎页在 120 秒内未稳定\n' >&2
  return 1
}

test_installer_ui() {
  local desktop_timeout=${DESKTOP_TIMEOUT_SECONDS:-600}
  local stability_seconds=${FRAMEBUFFER_STABILITY_SECONDS:-15}

  [[ $desktop_timeout =~ ^[0-9]+$ && $desktop_timeout -ge 60 && $desktop_timeout -le 1200 ]] || {
    printf '[ERROR] DESKTOP_TIMEOUT_SECONDS 必须在 60 到 1200 之间\n' >&2
    exit 2
  }
  [[ $stability_seconds =~ ^[0-9]+$ && $stability_seconds -ge 5 && $stability_seconds -le 60 ]] || {
    printf '[ERROR] FRAMEBUFFER_STABILITY_SECONDS 必须在 5 到 60 之间\n' >&2
    exit 2
  }
  command -v qemu-img >/dev/null 2>&1 || {
    printf '[ERROR] 缺少 qemu-img\n' >&2
    exit 1
  }
  if [[ ${INSTALLER_FULL_INSTALL:-0} == 1 ]]; then
    validate_installation_timeouts
  fi

  require_inputs
  disable_installer_network
  rm -f -- "$INSTALLER_DISK" "$INSTALLER_BASELINE" "$INSTALLER_SCREENSHOT" \
    "$MONITOR_SOCKET" "$SERIAL_SOCKET" "$SERIAL_COMMAND_PIPE"
  qemu-img create -q -f qcow2 "$INSTALLER_DISK" 32G
  : >"$SERIAL_LOG"
  qemu-system-x86_64 "${QEMU_ARGUMENTS[@]}" \
    -drive "if=virtio,format=qcow2,file=$INSTALLER_DISK" \
    -display none \
    -monitor "unix:$MONITOR_SOCKET,server=on,wait=off" \
    -serial "unix:$SERIAL_SOCKET,server=on,wait=off" &
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
  wait_for_framebuffer "$INSTALLER_BASELINE" 60
  login_live_console
  launch_installer
  wait_for_installer_stability
  run_guest_command \
    "sudo journalctl _SYSTEMD_USER_UNIT=lc300a-e2e-installer.service -n 80 --no-pager || true" \
    LC300A_INSTALLER_LOG 30
  wait_for_framebuffer "$INSTALLER_SCREENSHOT" 120 \
    --reference "$INSTALLER_BASELINE" --minimum-change-ratio 0.15
  printf '[OK] Calamares 已启动并绘制品牌欢迎页: %s\n' "$INSTALLER_SCREENSHOT"
  if [[ ${INSTALLER_WALK_PAGES:-0} == 1 ]]; then
    walk_installer_pages
  fi
  if [[ ${INSTALLER_FULL_INSTALL:-0} == 1 ]]; then
    complete_installer
    boot_installed_system
  fi
}

case ${1:-} in
  ui) test_installer_ui ;;
  walk) INSTALLER_WALK_PAGES=1 test_installer_ui ;;
  install) INSTALLER_FULL_INSTALL=1 test_installer_ui ;;
  *)
    printf '[ERROR] 用法: %s [ui|walk|install]\n' "$0" >&2
    exit 2
    ;;
esac
