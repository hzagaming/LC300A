#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_PATH = PROJECT_ROOT / "branding/product.toml"
EXPERIENCE_PATH = PROJECT_ROOT / "branding/experience.toml"
PACKAGE_LISTS = PROJECT_ROOT / "distro/package-lists"
OVERLAYS = PROJECT_ROOT / "distro/overlays"
HOOKS = PROJECT_ROOT / "distro/hooks"
DEFAULT_WORKSPACE = PROJECT_ROOT / "build/live-build/work"


def product_config() -> dict:
    return tomllib.loads(PRODUCT_PATH.read_text(encoding="utf-8"))


def experience_config() -> dict:
    return tomllib.loads(EXPERIENCE_PATH.read_text(encoding="utf-8"))


def quote_release(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ('"', "$", "`"):
        escaped = escaped.replace(character, f"\\{character}")
    return f'"{escaped}"'


def release_files(product: dict) -> dict[str, str]:
    metadata = product["product"]
    identity = product["identity"]
    base = product["base"]
    pretty_name = f'{metadata["display_name"]} {metadata["version"]}'
    live_hostname = f'{identity["hostname_prefix"]}-live'
    live_full_name = f'{metadata["name"]} Live User'
    base_name = f'debian:{base["suite"]}'
    os_release = "\n".join(
        (
            f'PRETTY_NAME={quote_release(pretty_name)}',
            f'NAME={quote_release(metadata["name"])}',
            f'VERSION={quote_release(metadata["version"])}',
            f'VERSION_ID={quote_release(metadata["version_id"])}',
            f'VERSION_CODENAME={quote_release(base["suite"])}',
            f'ID={quote_release(identity["os_release_id"])}',
            'ID_LIKE="debian"',
            f'HOME_URL={quote_release(identity["home_url"])}',
            f'SUPPORT_URL={quote_release(identity["support_url"])}',
            "",
        )
    )
    lc300a_release = "\n".join(
        (
            f'LC300A_NAME={quote_release(metadata["display_name"])}',
            f'LC300A_VERSION={quote_release(metadata["version"])}',
            f'LC300A_VERSION_ID={quote_release(metadata["version_id"])}',
            f'LC300A_CHANNEL={quote_release(metadata["channel"])}',
            f'LC300A_BASE={quote_release(base_name)}',
            "",
        )
    )
    live_config = "\n".join(
        (
            f'LIVE_HOSTNAME={quote_release(live_hostname)}',
            f'LIVE_USERNAME={quote_release(identity["live_user"])}',
            f'LIVE_USER_FULLNAME={quote_release(live_full_name)}',
            'LIVE_USER_DEFAULT_GROUPS="audio cdrom dip floppy video plugdev netdev sudo"',
            'LIVE_USER_DEFAULT_LOCALES="en_US.UTF-8"',
            "",
        )
    )
    sudoers = f'{identity["live_user"]} ALL=(ALL:ALL) NOPASSWD: ALL\n'
    sddm = "\n".join(
        (
            "[Autologin]",
            f'User={identity["live_user"]}',
            "Session=plasma",
            "Relogin=false",
            "",
            "[Theme]",
            "Current=breeze",
            "",
        )
    )
    return {
        "usr/lib/os-release": os_release,
        "etc/lc300a-release": lc300a_release,
        "etc/live/config.conf.d/lc300a.conf": live_config,
        "etc/sudoers.d/010_lc300a-live": sudoers,
        "etc/sddm.conf.d/lc300a.conf": sddm,
    }


def brand_assets() -> dict[Path, str]:
    experience = experience_config()
    sound_theme_path = PROJECT_ROOT / experience["assets"]["sound_theme"]
    sound_theme = tomllib.loads(sound_theme_path.read_text(encoding="utf-8"))
    assets = {
        PROJECT_ROOT / experience["assets"]["logo"]: "usr/share/pixmaps/lc300a-mark.svg",
        PROJECT_ROOT / experience["assets"]["wallpaper_light"]: (
            "usr/share/wallpapers/LC300AFlow/contents/images/3840x2160.svg"
        ),
        PROJECT_ROOT / experience["assets"]["wallpaper_dark"]: (
            "usr/share/wallpapers/LC300AFlow/contents/images_dark/3840x2160.svg"
        ),
    }
    destinations = {
        "startup": "usr/share/sounds/luochuan-flow/stereo/desktop-login.wav",
        "notification": "usr/share/sounds/luochuan-flow/stereo/message-new-instant.wav",
        "warning": "usr/share/sounds/luochuan-flow/stereo/dialog-warning.wav",
        "ambient": "usr/share/sounds/luochuan-flow/preview/ambient-preview.wav",
    }
    for sound_id, destination in destinations.items():
        assets[sound_theme_path.parent / sound_theme["sounds"][sound_id]["file"]] = destination
    return assets


def live_boot_parameters(product: dict, graphical: bool = True) -> str:
    identity = product["identity"]
    parameters = (
        "boot=live",
        "components",
        f'username={identity["live_user"]}',
        f'hostname={identity["hostname_prefix"]}-live',
        "locales=en_US.UTF-8,zh_CN.UTF-8",
        "keyboard-layouts=us",
        "utc=yes",
        "console=tty0",
        "console=ttyS0,115200n8",
    )
    if graphical:
        parameters += (
            "systemd.unit=graphical.target",
            "quiet",
            "splash",
            "loglevel=3",
            "systemd.show_status=auto",
            "udev.log_level=3",
            "plymouth.ignore-serial-consoles",
            "vt.global_cursor_default=0",
        )
    else:
        parameters += ("systemd.unit=multi-user.target",)
    return " ".join(parameters)


def grub_config(product: dict) -> str:
    title = product["product"]["display_name"].replace('"', '\\"')
    return "\n".join(
        (
            "set default=0",
            "set timeout=3",
            "",
            f'menuentry "{title} Live (图形桌面)" {{',
            f"    linux /live/vmlinuz {live_boot_parameters(product)}",
            "    initrd /live/initrd.img",
            "}",
            "",
            f'menuentry "{title} Live (纯文字模式)" {{',
            f"    linux /live/vmlinuz {live_boot_parameters(product, False)}",
            "    initrd /live/initrd.img",
            "}",
            "",
        )
    )


def iso_volume(product: dict) -> str:
    metadata = product["product"]
    return f'{metadata["name"]}_{metadata["version_id"]}'.replace(".", "_")[:32]


def live_build_arguments(product: dict) -> list[str]:
    metadata = product["product"]
    base = product["base"]
    return [
        "lb",
        "config",
        "--mode",
        "debian",
        "--system",
        "live",
        "--architectures",
        base["architecture"],
        "--distribution",
        base["suite"],
        "--archive-areas",
        "main contrib non-free-firmware",
        "--binary-images",
        "iso-hybrid",
        "--debian-installer",
        "false",
        "--firmware-chroot",
        "false",
        "--firmware-binary",
        "false",
        "--initsystem",
        "systemd",
        "--chroot-filesystem",
        "squashfs",
        "--compression",
        "xz",
        "--checksums",
        "sha256",
        "--apt-recommends",
        "true",
        "--security",
        "false",
        "--backports",
        "false",
        "--memtest",
        "none",
        "--iso-application",
        metadata["display_name"],
        "--iso-publisher",
        "LC300A Project",
        "--iso-volume",
        iso_volume(product),
        "--bootappend-live",
        live_boot_parameters(product),
    ]


def assemble_inputs(workspace: Path, product: dict) -> None:
    config = workspace / "config"
    package_target = config / "package-lists"
    overlay_target = config / "includes.chroot"
    hooks_root = config / "hooks"
    hook_target = hooks_root / "live"
    archives_target = config / "archives"
    boot_target = workspace / "lc300a-boot"
    for target in (package_target, overlay_target, hooks_root, archives_target):
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
    hook_target.mkdir()
    if boot_target.exists():
        shutil.rmtree(boot_target)
    boot_target.mkdir()

    for source in sorted(PACKAGE_LISTS.glob("*.list.chroot")):
        shutil.copy2(source, package_target / source.name)
    shutil.copytree(
        OVERLAYS,
        overlay_target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".gitkeep"),
    )
    for source, relative in brand_assets().items():
        target = overlay_target / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for source in sorted(HOOKS.glob("*.hook.chroot")):
        for target in (hooks_root / source.name, hook_target / source.name):
            shutil.copy2(source, target)
            target.chmod(0o755)
    for relative, content in release_files(product).items():
        target = overlay_target / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    security_source = (
        "deb http://security.debian.org/debian-security "
        f'{product["base"]["suite"]}-security main contrib non-free-firmware\n'
    )
    for suffix in ("chroot", "binary"):
        (archives_target / f"lc300a-security.list.{suffix}").write_text(
            security_source, encoding="utf-8"
        )
    (boot_target / "grub.cfg").write_text(grub_config(product), encoding="utf-8")
    (boot_target / "volume-id").write_text(iso_volume(product) + "\n", encoding="ascii")


def configure(workspace: Path, run_live_build: bool) -> None:
    product = product_config()
    if product["base"] != {
        "distribution": "debian",
        "suite": "trixie",
        "architecture": "amd64",
        "firmware": "uefi",
    }:
        raise ValueError("product base configuration does not match the supported build target")
    workspace.mkdir(parents=True, exist_ok=True)
    if run_live_build:
        subprocess.run(live_build_arguments(product), cwd=workspace, check=True)
    else:
        (workspace / "config").mkdir(exist_ok=True)
    assemble_inputs(workspace, product)


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure the LC300A live-build workspace")
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--assemble-only", action="store_true")
    arguments = parser.parse_args()
    try:
        configure(arguments.workspace.resolve(), not arguments.assemble_only)
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"[ERROR] live-build 配置失败: {error}", file=sys.stderr)
        return 1
    print(f"[OK] live-build 配置已生成: {arguments.workspace.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
