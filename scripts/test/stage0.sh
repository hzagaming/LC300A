#!/usr/bin/env bash

set -Eeuo pipefail
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly SCRIPT_DIR
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
readonly PROJECT_ROOT
cd "$PROJECT_ROOT"

required_files=(
  README.md ROADMAP.md PROJECT_STATE.md DECISIONS.md SECURITY.md Makefile
  .editorconfig .gitattributes .gitignore
  branding/experience.toml branding/product.toml docs/architecture/brand-experience.md
  docs/architecture/iso-build.md scripts/build/configure_live.py
  scripts/build/generate_sounds.py scripts/build/live_build.sh scripts/test/qemu-boot.sh
  scripts/bootstrap/debian.sh scripts/bootstrap/ubuntu.sh scripts/bootstrap/macos.sh
  scripts/test/bootstrap.sh scripts/test/clean.sh scripts/test/os-release.sh
  .github/workflows/ci.yml
)
required_directories=(
  apps/app-center apps/recovery apps/settings apps/system-report apps/updater apps/welcome
  branding/icons branding/logos branding/sounds branding/themes branding/wallpapers
  build/artifacts build/iso build/live-build build/rootfs
  desktop/defaults desktop/plasma desktop/sddm desktop/session
  distro/apt distro/boot distro/flatpak distro/hooks distro/overlays distro/package-lists
  distro/policies distro/systemd
  docs/architecture docs/development docs/installation docs/packaging docs/release docs/security
  installer/branding installer/calamares installer/modules
  packages/debian packages/manifests packages/repository
  services/hardware-daemon services/recovery-daemon services/settings-daemon services/update-daemon
  tests/boot tests/desktop tests/installer tests/integration tests/security tests/unit
)

for path in "${required_files[@]}"; do
  [[ -s $path ]] || {
    printf '[ERROR] 缺少阶段 0 文件或文件为空: %s\n' "$path" >&2
    exit 1
  }
done

for path in \
  distro/hooks/010-system-defaults.hook.chroot \
  distro/overlays/usr/libexec/lc300a/boot-ready \
  scripts/build/live_build.sh \
  scripts/test/qemu-boot.sh; do
  [[ -x $path ]] || {
    printf '[ERROR] 系统脚本不可执行: %s\n' "$path" >&2
    exit 1
  }
done

for path in "${required_directories[@]}"; do
  [[ -d $path ]] || {
    printf '[ERROR] 缺少阶段 0 目录: %s\n' "$path" >&2
    exit 1
  }
done

python3 scripts/test/validate_product.py
python3 scripts/test/validate_experience.py
python3 scripts/test/validate_live_build.py
python3 scripts/test/validate_desktop.py
python3 scripts/build/generate_sounds.py --check
python3 scripts/test/repository_hygiene.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/unit -p 'test_*.py'
./scripts/test/os-release.sh
./scripts/test/bootstrap.sh
./scripts/test/clean.sh

git check-ignore -q build/artifacts/LC300A-test.iso || {
  printf '[ERROR] build/artifacts 中的生成物未被 Git 忽略\n' >&2
  exit 1
}
if git check-ignore -q build/artifacts/.gitkeep; then
  printf '[ERROR] build/artifacts/.gitkeep 不应被 Git 忽略\n' >&2
  exit 1
fi
for path in .DS_Store .env __pycache__/module.pyc LC300A-test.iso; do
  git check-ignore -q "$path" || {
    printf '[ERROR] 仓库卫生规则未忽略: %s\n' "$path" >&2
    exit 1
  }
done
if git check-ignore -q .env.example; then
  printf '[ERROR] .env.example 应允许作为脱敏配置模板提交\n' >&2
  exit 1
fi

eol_attribute=$(git check-attr eol -- scripts/bootstrap/doctor.sh)
grep -q 'eol: lf$' <<<"$eol_attribute" || {
  printf '[ERROR] Shell 脚本未强制使用 LF 行尾\n' >&2
  exit 1
}

help_output=$(make --no-print-directory help)
grep -q 'make doctor' <<<"$help_output"
grep -q 'make iso' <<<"$help_output"

if make --no-print-directory clean >/dev/null 2>&1; then
  printf '[ERROR] 未确认时不应允许清理构建目录\n' >&2
  exit 1
fi
if BOOT_TIMEOUT_SECONDS=1 ./scripts/test/qemu-boot.sh test >/dev/null 2>&1; then
  printf '[ERROR] 启动测试接受了不安全的超时值\n' >&2
  exit 1
fi

printf '[OK] 项目文件、目录、配置、产物隔离、命令入口和阶段门禁测试通过\n'
