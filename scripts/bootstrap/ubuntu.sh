#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
# shellcheck source=/dev/null
source "$SCRIPT_DIR/lib.sh"

require_supported_linux_release ubuntu

mode=${1:---check}
case $mode in
  --check)
    check_commands "${LC300A_REQUIRED_COMMANDS[@]}" "${LC300A_LINUX_BUILD_COMMANDS[@]}"
    ;;
  --install)
    [[ $(uname -m) == x86_64 || $(uname -m) == amd64 ]] || {
      print_status ERROR "ISO 构建环境必须是 x86_64，当前为 $(uname -m)"
      exit 1
    }
    require_confirmation "将通过 apt 安装 LC300A 构建依赖，是否继续？" || exit 1
    run_as_root apt-get update
    install_linux_packages "${LC300A_LINUX_BUILD_PACKAGES[@]}"
    "$SCRIPT_DIR/doctor.sh" --strict
    ;;
  *)
    print_status ERROR "用法: $0 [--check|--install]"
    exit 2
    ;;
esac
