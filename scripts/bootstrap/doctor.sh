#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
# shellcheck source=/dev/null
source "$SCRIPT_DIR/lib.sh"

strict=0
if [[ ${1:-} == --strict ]]; then
  strict=1
elif [[ $# -gt 0 ]]; then
  print_status ERROR "未知参数: $1"
  exit 2
fi

os_name=$(uname -s)
machine=$(uname -m)
print_status INFO "宿主系统: $os_name $machine"
print_status INFO "目标系统: Linux x86_64 (amd64), UEFI"

missing=0
build_host=0
check_commands "${LC300A_REQUIRED_COMMANDS[@]}" || missing=1
if python3 -c 'import sys, tomllib; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
  print_status OK "Python: $(python3 -c 'import platform; print(platform.python_version())')，支持 tomllib"
else
  print_status MISSING "Python 3.11+（需要标准库 tomllib）"
  missing=1
fi

if [[ $os_name == Linux && ($machine == x86_64 || $machine == amd64) ]]; then
  build_host=1
  if is_supported_linux_release; then
    linux_id=$(os_release_value /etc/os-release ID)
    linux_version=$(os_release_value /etc/os-release VERSION_ID)
    print_status OK "宿主机可用于 LC300A ISO 构建: $linux_id $linux_version"
  else
    print_status MISSING "受支持的发行版（Debian 13 或 Ubuntu 24.04）"
    missing=1
  fi
  check_commands "${LC300A_LINUX_BUILD_COMMANDS[@]}" || missing=1

  if [[ (-r /usr/share/OVMF/OVMF_CODE_4M.fd && -r /usr/share/OVMF/OVMF_VARS_4M.fd) \
    || (-r /usr/share/OVMF/OVMF_CODE.fd && -r /usr/share/OVMF/OVMF_VARS.fd) \
    || (-r /usr/share/edk2/ovmf/OVMF_CODE.fd && -r /usr/share/edk2/ovmf/OVMF_VARS.fd) ]]; then
    print_status OK "OVMF CODE/VARS 固件已找到"
  else
    print_status MISSING "OVMF CODE/VARS 固件"
    missing=1
  fi
else
  print_status WARN "当前宿主机不能用于最终 ISO 构建验收"
  if [[ $os_name == Darwin ]]; then
    print_status INFO "请使用 x86_64 Debian/Ubuntu 虚拟机或远程构建机；macOS 脚本只准备宿主工具"
    check_commands qemu-system-x86_64 shellcheck || true
  fi
  [[ $strict == 0 ]] || missing=1
fi

if [[ $build_host == 1 && $missing == 0 ]]; then
  print_status OK "环境检查通过"
  exit 0
fi

if [[ $strict == 1 ]]; then
  print_status ERROR "严格检查失败：完整构建依赖或受支持宿主机缺失"
  exit 1
fi

print_status WARN "诊断完成，但当前环境不能执行完整 ISO 构建；运行 make bootstrap 查看安装方案"
