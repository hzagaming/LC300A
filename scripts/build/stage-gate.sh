#!/usr/bin/env bash

set -Eeuo pipefail

target=${1:-unknown}
case $target in
  rootfs|iso|run|run-uefi|test-boot)
    stage=1
    ;;
  test-desktop)
    stage=2
    ;;
  test-installer)
    stage=3
    ;;
  release)
    stage=7
    ;;
  *)
    printf '[ERROR] 未知阶段命令: %s\n' "$target" >&2
    exit 2
    ;;
esac

printf '[ERROR] make %s 属于阶段 %s，当前阶段 0 尚未提供该功能。\n' "$target" "$stage" >&2
printf '[INFO] 当前唯一优先任务记录在 PROJECT_STATE.md。\n' >&2
exit 2
