#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR

case $(uname -s) in
  Darwin)
    exec "$SCRIPT_DIR/macos.sh" "$@"
    ;;
  Linux)
    if [[ -r /etc/os-release ]]; then
      # shellcheck disable=SC1091
      source /etc/os-release
    else
      printf '[ERROR] 无法识别 Linux 发行版：缺少 /etc/os-release\n' >&2
      exit 1
    fi
    case ${ID:-} in
      debian) exec "$SCRIPT_DIR/debian.sh" "$@" ;;
      ubuntu) exec "$SCRIPT_DIR/ubuntu.sh" "$@" ;;
      *)
        printf '[ERROR] 当前仅支持 Debian 或 Ubuntu 构建环境，检测到: %s\n' "${ID:-unknown}" >&2
        exit 1
        ;;
    esac
    ;;
  *)
    printf '[ERROR] 不支持的宿主系统: %s\n' "$(uname -s)" >&2
    exit 1
    ;;
esac
