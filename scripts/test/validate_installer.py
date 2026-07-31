#!/usr/bin/env python3

import importlib.util
import stat
import sys
import tempfile
import tomllib
from pathlib import Path


sys.dont_write_bytecode = True
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIGURE_SPEC = importlib.util.spec_from_file_location(
    "configure_live", PROJECT_ROOT / "scripts/build/configure_live.py"
)
CONFIGURE = importlib.util.module_from_spec(CONFIGURE_SPEC)
CONFIGURE_SPEC.loader.exec_module(CONFIGURE)


def require_text(path: Path, values: tuple[str, ...]) -> str:
    content = path.read_text(encoding="utf-8")
    for value in values:
        if value not in content:
            raise ValueError(f"{path.relative_to(PROJECT_ROOT)} 缺少: {value}")
    return content


def validate() -> None:
    product = tomllib.loads((PROJECT_ROOT / "branding/product.toml").read_text(encoding="utf-8"))[
        "product"
    ]
    packages = (
        PROJECT_ROOT / "distro/package-lists/installer.list.chroot"
    ).read_text(encoding="utf-8").splitlines()
    if packages != sorted(set(packages)):
        raise ValueError("安装器软件包清单必须排序且不能重复")
    required_packages = {
        "calamares",
        "calamares-settings-debian",
        "efibootmgr",
        "grub-efi",
        "grub-efi-amd64",
    }
    if not required_packages.issubset(packages):
        raise ValueError(f"安装器软件包清单缺少: {sorted(required_packages - set(packages))}")

    settings = require_text(
        PROJECT_ROOT / "installer/calamares/settings.conf",
        (
            "branding: lc300a",
            "hide-back-and-next-during-exec: true",
            "- partition",
            "- mount",
            "- unpackfs",
            "- users",
            "- bootloader",
            "- lc300a-configure",
            "- packages",
            "- umount",
            "- lc300a-finished",
        ),
    )
    for unsafe_module in ("sources-media", "sources-media-unmount", "sources-final"):
        if f"- {unsafe_module}" in settings:
            raise ValueError(f"自制 ISO 不得使用 Debian 安装介质仓库模块: {unsafe_module}")

    require_text(
        PROJECT_ROOT / "installer/modules/partition.conf",
        (
            'defaultFileSystemType: "ext4"',
            'efiSystemPartition: "/boot/efi"',
            'defaultPartitionTableType: "gpt"',
            'initialSwapChoice: "file"',
        ),
    )
    packages_config = require_text(
        PROJECT_ROOT / "installer/modules/packages.conf",
        ("backend: apt", "calamares", "calamares-settings-debian", "live-boot", "live-config"),
    )
    if packages_config.count("calamares-settings-debian") != 1:
        raise ValueError("安装后软件包清理清单存在重复项")
    if "live-task-" in packages_config:
        raise ValueError("安装后清理清单不得引用 Debian 13 中不存在的 live-task 包")

    require_text(
        PROJECT_ROOT / "installer/branding/branding.desc",
        (
            "componentName: lc300a",
            "productName: 落川OS 300型",
            f'version: {product["version"]}',
            f'shortVersion: {product["version_id"]}',
            "bootloaderEntryName: LC300A",
            'productLogo: "lc300a-mark.svg"',
            'slideshow: "show.qml"',
        ),
    )
    stylesheet = require_text(
        PROJECT_ROOT / "installer/branding/stylesheet.qss",
        ("min-height: 38px;", "QPushButton:focus", "QLineEdit:focus", "QComboBox:focus"),
    )
    if stylesheet.count("min-height: 38px;") != 2:
        raise ValueError("安装器按钮和输入框未达到 44px 交互目标")
    require_text(
        PROJECT_ROOT / "distro/overlays/usr/share/applications/lc300a-installer.desktop",
        ("Name=安装落川OS 300型", "Exec=lc300a-installer", "Terminal=false"),
    )
    require_text(
        PROJECT_ROOT / "distro/overlays/usr/local/bin/lc300a-installer",
        (
            "/run/live/medium",
            "sudo -E systemd-inhibit",
            'calamares "$@"',
            "trap restore_fstab",
        ),
    )
    require_text(
        PROJECT_ROOT / "distro/overlays/usr/share/calamares/helpers/lc300a-configure",
        (
            "/etc/sddm.conf.d/lc300a.conf",
            "/etc/sudoers.d/010_lc300a-live",
            "/etc/live/config.conf.d/lc300a.conf",
            "/etc/systemd/journald.conf.d/volatile.conf",
            "/etc/xdg/kscreenlockerrc",
            "/etc/xdg/powerdevilrc",
            "lc300a-installer.desktop",
            "trixie-security",
            "LC300A（落川OS 300型）开发版本",
            'GRUB_CMDLINE_LINUX="console=tty0 console=ttyS0,115200n8"',
            'chroot "$target" update-grub',
        ),
    )
    require_text(
        PROJECT_ROOT / "distro/overlays/usr/lib/calamares/modules/lc300a-configure/module.desc",
        ('name: "lc300a-configure"', 'interface: "process"'),
    )
    require_text(
        PROJECT_ROOT / "distro/overlays/usr/share/calamares/helpers/lc300a-finished",
        ("LC300A_INSTALL_OK", "[ -w /dev/ttyS0 ]"),
    )
    executables = (
        "distro/overlays/usr/local/bin/lc300a-installer",
        "distro/overlays/usr/libexec/lc300a/add-installer-launcher",
        "distro/overlays/usr/share/calamares/helpers/lc300a-configure",
        "distro/overlays/usr/share/calamares/helpers/lc300a-finished",
    )
    for relative in executables:
        if not (PROJECT_ROOT / relative).stat().st_mode & stat.S_IXUSR:
            raise ValueError(f"安装器脚本不可执行: {relative}")

    with tempfile.TemporaryDirectory(prefix="lc300a-installer-") as directory:
        workspace = Path(directory)
        CONFIGURE.configure(workspace, False)
        overlay = workspace / "config/includes.chroot"
        expected = (
            "etc/calamares/settings.conf",
            "etc/calamares/modules/partition.conf",
            "etc/calamares/modules/packages.conf",
            "etc/calamares/branding/lc300a/branding.desc",
            "etc/calamares/branding/lc300a/lc300a-mark.svg",
            "etc/calamares/branding/lc300a/welcome.svg",
            "etc/calamares/branding/lc300a/show.qml",
            "etc/calamares/branding/lc300a/stylesheet.qss",
            "usr/lib/calamares/modules/lc300a-finished/module.desc",
            "usr/share/calamares/helpers/lc300a-finished",
        )
        missing = [relative for relative in expected if not (overlay / relative).is_file()]
        if missing:
            raise ValueError(f"Live 文件系统缺少安装器配置: {missing}")

    require_text(
        PROJECT_ROOT / "scripts/test/qemu-installer.sh",
        (
            "qemu-img create -q -f qcow2",
            "LC300A_INSTALL_OK",
            "LC300A_INSTALLER_READY",
            "LC300A_INSTALLER_INHIBIT",
            "stable_frames",
            "select_erase_disk",
            "send_monitor_key spc",
            "installer-partition-choice.ppm",
            "installer-users.ppm",
            "installer-summary.ppm",
            "installer-installing.ppm",
            "INSTALLER_TIMEOUT_SECONDS:-3600",
            "alt-n",
            "alt-i",
            "RiverStone-300",
            "findmnt -n -o FSTYPE /",
            "test -x /usr/sbin/hwclock",
            "QEMU_ARGUMENTS[index+1]=none",
            "dpkg-query -W calamares",
            "LC300A_INSTALLED_DESKTOP_OK",
            "installer-test.qcow2",
        ),
    )
    require_text(
        PROJECT_ROOT / "Makefile",
        ("test-installer:", "qemu-installer.sh install"),
    )


def main() -> int:
    try:
        validate()
    except (OSError, ValueError) as error:
        print(f"[ERROR] 安装器契约校验失败: {error}", file=sys.stderr)
        return 1
    print("[OK] Calamares、UEFI/ext4、品牌与安装后清理契约通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
