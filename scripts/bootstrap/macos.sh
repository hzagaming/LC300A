#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
# shellcheck source=/dev/null
source "$SCRIPT_DIR/lib.sh"

mode=${1:---check}
machine=$(uname -m)
print_status INFO "macOS 架构: $machine"
[[ $machine == arm64 ]] && print_status WARN "Apple Silicon 不能原生验收 x86_64 LC300A ISO"

case $mode in
  --check)
    check_commands git make bash python3 || true
    check_commands brew qemu-system-x86_64 shellcheck || true
    ;;
  --install)
    has_command brew || {
      print_status ERROR "未找到 Homebrew。请从 https://brew.sh 安装并验证来源后重试"
      exit 1
    }
    require_confirmation "将通过 Homebrew 安装 QEMU 和 ShellCheck，是否继续？" || exit 1
    brew install qemu shellcheck
    ;;
  *)
    print_status ERROR "用法: $0 [--check|--install]"
    exit 2
    ;;
esac

cat <<'EOF'
[INFO] 最终构建方案：
  1. 准备 Debian 13 或 Ubuntu 24.04 x86_64 虚拟机/远程构建机。
  2. 克隆仓库并运行 make bootstrap、make doctor-strict。
  3. 在该 Linux 环境执行后续 make iso 与 make test-boot。
QEMU 在 Apple Silicon 上运行 x86_64 客体属于模拟，速度较慢，不能替代 x86_64 Linux 发布构建机。
EOF
