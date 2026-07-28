#!/usr/bin/env python3

import importlib.util
import stat
import sys
import tempfile
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIGURE_PATH = PROJECT_ROOT / "scripts/build/configure_live.py"
SPEC = importlib.util.spec_from_file_location("configure_live", CONFIGURE_PATH)
CONFIGURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONFIGURE)


def validate() -> None:
    product = tomllib.loads(
        (PROJECT_ROOT / "branding/product.toml").read_text(encoding="utf-8")
    )
    packages = (
        PROJECT_ROOT / "distro/package-lists/core.list.chroot"
    ).read_text(encoding="utf-8").splitlines()
    if packages != sorted(set(packages)):
        raise ValueError("核心软件包清单必须排序且不能重复")
    required = {
        "linux-image-amd64",
        "live-boot",
        "live-config",
        "plymouth",
        "plymouth-label",
        "plymouth-themes",
        "sudo",
        "systemd-sysv",
    }
    if not required.issubset(packages) or "openssh-server" in packages:
        raise ValueError("核心软件包清单缺少启动组件或意外启用 SSH 服务端")

    arguments = CONFIGURE.live_build_arguments(product)
    required_arguments = (
        (arguments, "--distribution", "trixie"),
        (arguments, "--architectures", "amd64"),
        (arguments, "--binary-images", "iso-hybrid"),
        (arguments, "--debian-installer", "false"),
        (arguments, "--security", "false"),
        (arguments, "--firmware-chroot", "false"),
        (arguments, "--firmware-binary", "false"),
        (arguments, "--initsystem", "systemd"),
    )
    for candidate, option, expected in required_arguments:
        index = candidate.index(option)
        if candidate[index + 1] != expected:
            raise ValueError(f"live-build 参数错误: {option}")
    if "--bootloader" in arguments or "--bootloaders" in arguments:
        raise ValueError("rootfs 配置不应依赖 live-build 的过时 binary bootloader")
    boot_parameters = arguments[arguments.index("--bootappend-live") + 1]
    for value in (
        "boot=live",
        "console=ttyS0,115200n8",
        "plymouth.ignore-serial-consoles",
        "quiet",
        "splash",
        "systemd.unit=graphical.target",
        "systemd.show_status=auto",
        "username=lc300a-live",
    ):
        if value not in boot_parameters:
            raise ValueError(f"缺少启动参数: {value}")

    with tempfile.TemporaryDirectory(prefix="lc300a-live-config-") as directory:
        workspace = Path(directory)
        CONFIGURE.configure(workspace, False)
        config = workspace / "config"
        if list(config.rglob(".gitkeep")):
            raise ValueError("Live 文件系统包含仓库占位文件")
        generated_packages = (config / "package-lists/core.list.chroot").read_text().splitlines()
        if generated_packages != packages:
            raise ValueError("生成的软件包清单与版本控制输入不一致")
        security_sources = {
            path.name: path.read_text(encoding="utf-8")
            for path in (config / "archives").glob("lc300a-security.list.*")
        }
        expected_security = (
            "deb http://security.debian.org/debian-security trixie-security "
            "main contrib non-free-firmware\n"
        )
        if security_sources != {
            "lc300a-security.list.binary": expected_security,
            "lc300a-security.list.chroot": expected_security,
        }:
            raise ValueError("Debian 安全更新源配置错误")
        overlay = config / "includes.chroot"
        os_release = (overlay / "usr/lib/os-release").read_text(encoding="utf-8")
        live_config = (overlay / "etc/live/config.conf.d/lc300a.conf").read_text(
            encoding="utf-8"
        )
        sudoers = (overlay / "etc/sudoers.d/010_lc300a-live").read_text(encoding="utf-8")
        plymouth_config = (overlay / "etc/plymouth/plymouthd.conf").read_text(
            encoding="utf-8"
        )
        plymouth_theme = overlay / "usr/share/plymouth/themes/lc300a"
        if 'ID="lc300a"' not in os_release or 'VERSION_CODENAME="trixie"' not in os_release:
            raise ValueError("生成的 os-release 身份错误")
        if 'LIVE_USERNAME="lc300a-live"' not in live_config:
            raise ValueError("Live 用户配置未从产品配置生成")
        if sudoers != "lc300a-live ALL=(ALL:ALL) NOPASSWD: ALL\n":
            raise ValueError("Live sudoers 配置错误")
        if "Theme=lc300a" not in plymouth_config:
            raise ValueError("Plymouth 未选择 LC300A 图形启动主题")
        for name in ("lc300a-mark.png", "lc300a.plymouth", "lc300a.script"):
            if not (plymouth_theme / name).is_file():
                raise ValueError(f"Plymouth 主题缺少文件: {name}")
        plymouth_script = (plymouth_theme / "lc300a.script").read_text(encoding="utf-8")
        if "Image.Solid" in plymouth_script:
            raise ValueError("Plymouth 主题使用当前 script 插件不支持的 Image.Solid")
        for value in ("Plymouth.SetRefreshFunction", "SetOpacity"):
            if value not in plymouth_script:
                raise ValueError(f"Plymouth 启动状态动画缺少: {value}")
        service = (overlay / "usr/lib/systemd/system/lc300a-boot-ready.service").read_text(
            encoding="utf-8"
        )
        marker_script = (overlay / "usr/libexec/lc300a/boot-ready").read_text(
            encoding="utf-8"
        )
        if (
            "WantedBy=multi-user.target" not in service
            or "After=live-config.service" not in service
            or "LC300A_BOOT_OK" not in marker_script
            or "LC300A_CONSOLE_OK" not in marker_script
            or 'id "$LIVE_USERNAME"' not in marker_script
            or "getty@tty1.service" in service
            or "getty@tty1.service" in marker_script
        ):
            raise ValueError("串口启动标记服务配置错误")
        modern_hook = config / "hooks/live/010-system-defaults.hook.chroot"
        legacy_hook = config / "hooks/010-system-defaults.hook.chroot"
        if (
            modern_hook.read_bytes() != legacy_hook.read_bytes()
            or not modern_hook.stat().st_mode & stat.S_IXUSR
            or not legacy_hook.stat().st_mode & stat.S_IXUSR
        ):
            raise ValueError("新旧 live-build chroot hook 布局不一致或不可执行")
        hook = modern_hook.read_text(encoding="utf-8")
        for value in ("plymouth-set-default-theme lc300a", "update-initramfs -u"):
            if value not in hook:
                raise ValueError(f"Plymouth initramfs 集成缺少: {value}")

        grub = (workspace / "lc300a-boot/grub.cfg").read_text(encoding="utf-8")
        for value in (
            'menuentry "落川OS 300型 Live (图形桌面)"',
            'menuentry "落川OS 300型 Live (纯文字模式)"',
            "systemd.unit=graphical.target",
            "systemd.unit=multi-user.target",
        ):
            if value not in grub:
                raise ValueError(f"GRUB 启动模式选择缺少: {value}")

    qemu_script = (PROJECT_ROOT / "scripts/test/qemu-boot.sh").read_text(encoding="utf-8")
    for value in (
        "OVMF_CODE_4M.fd",
        "OVMF_VARS_4M.fd",
        "edk2-x86_64-code.fd",
        "edk2-i386-vars.fd",
        "if=pflash",
        "LC300A_BOOT_OK",
        "LC300A_CONSOLE_OK",
        "LC300A_ISO_PATH",
        "CONSOLE_TIMEOUT_SECONDS",
        'for key in ("down", "ret")',
        "QEMU_PID=",
    ):
        if value not in qemu_script:
            raise ValueError(f"QEMU UEFI 测试缺少契约: {value}")
    if "local qemu_pid" in qemu_script:
        raise ValueError("QEMU 清理 trap 不应引用已离开作用域的局部 PID")
    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")
    if "test-console:" not in makefile or "qemu-boot.sh console" not in makefile:
        raise ValueError("Makefile 缺少纯文字模式验收入口")
    build_script = (PROJECT_ROOT / "scripts/build/live_build.sh").read_text(encoding="utf-8")
    for value in (
        "grub-mkrescue",
        "lb clean --chroot --stage",
        "mksquashfs",
        "sha256sum.txt",
        "-report_el_torito",
    ):
        if value not in build_script:
            raise ValueError(f"UEFI ISO 组装缺少契约: {value}")


def main() -> int:
    try:
        validate()
    except (KeyError, OSError, ValueError) as error:
        print(f"[ERROR] live-build 契约校验失败: {error}", file=sys.stderr)
        return 1
    print("[OK] live-build 参数、软件包、overlay 与 hook 契约通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
