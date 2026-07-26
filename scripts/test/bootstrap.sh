#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
# shellcheck source=/dev/null
source "$SCRIPT_DIR/../bootstrap/lib.sh"

[[ " ${LC300A_LINUX_BUILD_PACKAGES[*]} " == *" debian-archive-keyring "* ]] || {
  printf '[ERROR] Linux 构建依赖缺少 Debian 软件源签名 keyring\n' >&2
  exit 1
}

captured_command=
run_as_root() {
  printf -v captured_command '%q ' "$@"
}

LC300A_ASSUME_YES=1 install_linux_packages package-one package-two
[[ $captured_command == 'apt-get install --no-install-recommends --yes package-one package-two ' ]] || {
  printf '[ERROR] 非交互安装未向 apt-get 传递 --yes: %s\n' "$captured_command" >&2
  exit 1
}

unset LC300A_ASSUME_YES
install_linux_packages package-one
[[ $captured_command == 'apt-get install --no-install-recommends package-one ' ]] || {
  printf '[ERROR] 交互安装不应强制 apt-get --yes: %s\n' "$captured_command" >&2
  exit 1
}

printf '[OK] bootstrap 非交互安装契约通过\n'
