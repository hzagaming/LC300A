#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_PATH = PROJECT_ROOT / "branding/product.toml"
PACKAGE_LISTS = PROJECT_ROOT / "distro/package-lists"
OVERLAYS = PROJECT_ROOT / "distro/overlays"
HOOKS = PROJECT_ROOT / "distro/hooks"
DEFAULT_WORKSPACE = PROJECT_ROOT / "build/live-build/work"


def product_config() -> dict:
    return tomllib.loads(PRODUCT_PATH.read_text(encoding="utf-8"))


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
    return {
        "usr/lib/os-release": os_release,
        "etc/lc300a-release": lc300a_release,
        "etc/live/config.conf.d/lc300a.conf": live_config,
        "etc/sudoers.d/010_lc300a-live": sudoers,
    }


def live_build_arguments(product: dict) -> list[str]:
    metadata = product["product"]
    identity = product["identity"]
    base = product["base"]
    volume = f'{metadata["name"]}_{metadata["version_id"]}'.replace(".", "_")[:32]
    boot_parameters = " ".join(
        (
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
    )
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
        "--bootloaders",
        "grub-efi",
        "--debian-installer",
        "none",
        "--chroot-filesystem",
        "squashfs",
        "--compression",
        "xz",
        "--checksums",
        "sha256",
        "--apt-recommends",
        "true",
        "--security",
        "true",
        "--updates",
        "true",
        "--backports",
        "false",
        "--memtest",
        "none",
        "--image-name",
        identity["os_release_id"],
        "--iso-application",
        metadata["display_name"],
        "--iso-publisher",
        "LC300A Project",
        "--iso-volume",
        volume,
        "--bootappend-live",
        boot_parameters,
    ]


def assemble_inputs(workspace: Path, product: dict) -> None:
    config = workspace / "config"
    package_target = config / "package-lists"
    overlay_target = config / "includes.chroot"
    hook_target = config / "hooks/live"
    for target in (package_target, overlay_target, hook_target):
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)

    for source in sorted(PACKAGE_LISTS.glob("*.list.chroot")):
        shutil.copy2(source, package_target / source.name)
    shutil.copytree(
        OVERLAYS,
        overlay_target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".gitkeep"),
    )
    for source in sorted(HOOKS.glob("*.hook.chroot")):
        target = hook_target / source.name
        shutil.copy2(source, target)
        target.chmod(0o755)
    for relative, content in release_files(product).items():
        target = overlay_target / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def configure(workspace: Path, run_live_build: bool) -> None:
    product = product_config()
    if product["base"] != {
        "distribution": "debian",
        "suite": "trixie",
        "architecture": "amd64",
        "firmware": "uefi",
    }:
        raise ValueError("product base configuration does not match stage 1")
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
