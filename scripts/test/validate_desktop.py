#!/usr/bin/env python3

import configparser
import importlib.util
import json
import sys
import tempfile
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = PROJECT_ROOT / "distro/overlays"
DESKTOP_PACKAGES = PROJECT_ROOT / "distro/package-lists/desktop.list.chroot"
BRANDING = PROJECT_ROOT / "branding"
CONFIGURE_SPEC = importlib.util.spec_from_file_location(
    "configure_live", PROJECT_ROOT / "scripts/build/configure_live.py"
)
CONFIGURE = importlib.util.module_from_spec(CONFIGURE_SPEC)
CONFIGURE_SPEC.loader.exec_module(CONFIGURE)
EXPERIENCE_SPEC = importlib.util.spec_from_file_location(
    "validate_experience", PROJECT_ROOT / "scripts/test/validate_experience.py"
)
EXPERIENCE_VALIDATOR = importlib.util.module_from_spec(EXPERIENCE_SPEC)
EXPERIENCE_SPEC.loader.exec_module(EXPERIENCE_VALIDATOR)


def read_config(relative: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser(interpolation=None)
    with (OVERLAY / relative).open(encoding="utf-8") as stream:
        config.read_file(stream)
    return config


def validate_packages() -> None:
    packages = DESKTOP_PACKAGES.read_text(encoding="utf-8").splitlines()
    if packages != sorted(set(packages)):
        raise ValueError("桌面软件包清单必须排序且不能重复")
    core_packages = (PROJECT_ROOT / "distro/package-lists/core.list.chroot").read_text(
        encoding="utf-8"
    ).splitlines()
    installed = set(packages) | set(core_packages)
    required = {
        "dolphin",
        "firefox-esr",
        "flatpak",
        "fonts-noto-cjk",
        "konsole",
        "kwin-wayland",
        "network-manager",
        "packagekit",
        "pipewire-pulse",
        "plasma-desktop",
        "plasma-discover",
        "plasma-discover-backend-flatpak",
        "plasma-nm",
        "plasma-pa",
        "plasma-workspace",
        "sddm",
        "sddm-theme-breeze",
        "systemsettings",
        "wireplumber",
        "xwayland",
    }
    if not required.issubset(installed):
        raise ValueError(f"桌面软件包清单缺少组件: {sorted(required - installed)}")
    forbidden = {"openssh-server", "plasma-workspace-wayland", "pulseaudio"}
    if forbidden & installed:
        raise ValueError(f"桌面软件包清单包含禁用组件: {sorted(forbidden & installed)}")


def validate_sddm() -> None:
    product = tomllib.loads((BRANDING / "product.toml").read_text(encoding="utf-8"))
    config = configparser.ConfigParser(interpolation=None)
    config.read_string(CONFIGURE.release_files(product)["etc/sddm.conf.d/lc300a.conf"])
    if dict(config["Autologin"]) != {
        "user": "lc300a-live",
        "session": "plasma",
        "relogin": "false",
    }:
        raise ValueError("SDDM Live 自动登录配置错误")
    if config["Theme"].get("current") != "breeze":
        raise ValueError("SDDM 未启用 Breeze 品牌基础主题")

    theme = read_config("usr/share/sddm/themes/breeze/theme.conf.user")
    general = theme["General"]
    if general.get("background") != "/usr/share/wallpapers/LC300AFlow/contents/images/3840x2160.svg":
        raise ValueError("SDDM 背景未使用 LC300A 壁纸")
    if general.get("logo") != "/usr/share/pixmaps/lc300a-mark.svg" or general.get("showlogo") != "shown":
        raise ValueError("SDDM Logo 配置错误")


def validate_plasma() -> None:
    look_and_feel = OVERLAY / "usr/share/plasma/look-and-feel/org.lc300a.desktop"
    metadata = json.loads((look_and_feel / "metadata.json").read_text(encoding="utf-8"))
    if metadata["KPackageStructure"] != "Plasma/LookAndFeel":
        raise ValueError("Plasma Look-and-Feel 元数据错误")
    if metadata["KPlugin"]["Id"] != "org.lc300a.desktop":
        raise ValueError("Plasma Look-and-Feel ID 错误")
    defaults = (look_and_feel / "contents/defaults").read_text(encoding="utf-8")
    for value in (
        "ColorScheme=LuochuanFlow",
        "Image=LC300AFlow",
        "cursorTheme=breeze_cursors",
        "Theme=org.kde.Breeze",
    ):
        if value not in defaults:
            raise ValueError(f"Plasma 默认体验缺少: {value}")

    kdeglobals = read_config("etc/xdg/kdeglobals")
    if kdeglobals["KDE"].get("lookandfeelpackage") != "org.lc300a.desktop":
        raise ValueError("系统未选择 LC300A Look-and-Feel")
    if kdeglobals["General"].get("colorscheme") != "LuochuanFlow":
        raise ValueError("系统未选择落川流光配色")
    if kdeglobals["Sounds"].get("theme") != "luochuan-flow":
        raise ValueError("系统未选择落川流光声音主题")

    welcome = read_config("etc/xdg/plasma-welcomerc")
    if welcome["General"].get("lastseenversion") != "6.3.4":
        raise ValueError("Plasma Welcome Center 首次自动弹窗未关闭")

    required_assets = (
        "usr/share/color-schemes/LuochuanFlow.colors",
        "usr/share/wallpapers/LC300AFlow/metadata.json",
    )
    for relative in required_assets:
        if not (OVERLAY / relative).is_file():
            raise ValueError(f"缺少桌面品牌资产: {relative}")

    favorites = read_config("etc/xdg/kicker-extra-favoritesrc")["General"]
    expected = [
        "firefox-esr.desktop",
        "org.kde.discover.desktop",
        "org.kde.dolphin.desktop",
        "org.kde.konsole.desktop",
    ]
    if favorites.get("prepend", "").split(";") != expected:
        raise ValueError("应用菜单未固定浏览器、应用商店、文件管理器和终端")
    if favorites.getboolean("ignoredefaults", fallback=True):
        raise ValueError("应用菜单不应隐藏 Plasma 默认收藏")

    power = read_config("etc/xdg/powerdevilrc")
    for profile in ("AC", "Battery", "LowBattery"):
        settings = power[profile]
        if settings.getboolean("dimdisplaywhenidle", fallback=True):
            raise ValueError(f"{profile} Live 会话仍会自动调暗显示器")
        if settings.getboolean("turnoffdisplaywhenidle", fallback=True):
            raise ValueError(f"{profile} Live 会话仍会自动关闭显示器")
        if settings.getboolean("lockbeforeturnoffdisplay", fallback=True):
            raise ValueError(f"{profile} Live 会话仍会在关闭显示器前锁屏")

    locker = read_config("etc/xdg/kscreenlockerrc")["Daemon"]
    if locker.getboolean("autolock", fallback=True) or locker.getint("timeout", fallback=-1) != 0:
        raise ValueError("Live 会话仍会自动锁屏")


def validate_color_scheme() -> None:
    colors = read_config("usr/share/color-schemes/LuochuanFlow.colors")
    minimum = tomllib.loads((BRANDING / "experience.toml").read_text(encoding="utf-8"))[
        "accessibility"
    ]["minimum_text_contrast"]
    for section in ("Colors:Button", "Colors:Selection", "Colors:Tooltip", "Colors:View", "Colors:Window"):
        background = rgb_hex(colors[section]["BackgroundNormal"])
        for role, value in colors[section].items():
            if role.startswith("foreground"):
                ratio = EXPERIENCE_VALIDATOR.contrast_ratio(rgb_hex(value), background)
                if ratio < minimum:
                    raise ValueError(f"{section}.{role} 对比度仅 {ratio:.2f}:1")


def rgb_hex(value: str) -> str:
    channels = [int(channel) for channel in value.split(",")]
    if len(channels) != 3 or any(channel < 0 or channel > 255 for channel in channels):
        raise ValueError(f"KDE 颜色格式错误: {value}")
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def validate_audio() -> None:
    theme = read_config("usr/share/sounds/luochuan-flow/index.theme")
    if theme["Sound Theme"].get("directories") != "stereo":
        raise ValueError("freedesktop 声音主题目录错误")
    experience = tomllib.loads((BRANDING / "experience.toml").read_text(encoding="utf-8"))
    sound_theme_path = PROJECT_ROOT / experience["assets"]["sound_theme"]
    sound_theme = tomllib.loads(sound_theme_path.read_text(encoding="utf-8"))
    for sound in sound_theme["sounds"].values():
        if not (sound_theme_path.parent / sound["file"]).is_file():
            raise ValueError(f"缺少声音源资产: {sound['file']}")
    autostarts = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (OVERLAY / "etc/xdg/autostart").glob("*.desktop")
    )
    if "ambient-preview" in autostarts or "background_music" in autostarts:
        raise ValueError("BGM 不得自动启动")


def validate_assembled_assets() -> None:
    expected = {
        "usr/share/pixmaps/lc300a-mark.svg",
        "usr/share/wallpapers/LC300AFlow/contents/images/3840x2160.svg",
        "usr/share/wallpapers/LC300AFlow/contents/images_dark/3840x2160.svg",
        "usr/share/sounds/luochuan-flow/stereo/desktop-login.wav",
        "usr/share/sounds/luochuan-flow/stereo/dialog-warning.wav",
        "usr/share/sounds/luochuan-flow/stereo/message-new-instant.wav",
        "usr/share/sounds/luochuan-flow/preview/ambient-preview.wav",
    }
    with tempfile.TemporaryDirectory(prefix="lc300a-desktop-") as directory:
        workspace = Path(directory)
        CONFIGURE.configure(workspace, False)
        overlay = workspace / "config/includes.chroot"
        missing = sorted(relative for relative in expected if not (overlay / relative).is_file())
        if missing:
            raise ValueError(f"Live 文件系统缺少品牌资产: {missing}")


def validate_readiness() -> None:
    hook = (PROJECT_ROOT / "distro/hooks/010-system-defaults.hook.chroot").read_text(
        encoding="utf-8"
    )
    if "systemctl set-default graphical.target" not in hook:
        raise ValueError("桌面系统未默认进入 graphical.target")
    service = (OVERLAY / "usr/lib/systemd/system/lc300a-desktop-ready.service").read_text(
        encoding="utf-8"
    )
    probe = (OVERLAY / "usr/libexec/lc300a/desktop-ready").read_text(encoding="utf-8")
    shell_wrapper = (OVERLAY / "usr/libexec/lc300a/start-plasmashell").read_text(encoding="utf-8")
    shell_drop_in = (
        OVERLAY / "etc/systemd/user/plasma-plasmashell.service.d/lc300a.conf"
    ).read_text(encoding="utf-8")
    kwin_wrapper = (OVERLAY / "usr/libexec/lc300a/start-kwin-wayland").read_text(
        encoding="utf-8"
    )
    kwin_drop_in = (
        OVERLAY / "etc/systemd/user/plasma-kwin_wayland.service.d/lc300a.conf"
    ).read_text(encoding="utf-8")
    for value in ("display-manager.service", "TimeoutStartSec=300", "WantedBy=graphical.target"):
        if value not in service:
            raise ValueError(f"桌面就绪服务缺少: {value}")
    for value in (
        "kwin_wayland",
        "plasmashell",
        "org.kde.plasmashell",
        "pipewire",
        "wireplumber",
        "/sys/class/drm",
        "LC300A_DESKTOP_OK",
        "packagekit-backend.so",
        "plasma-discover",
    ):
        if value not in probe:
            raise ValueError(f"桌面就绪探针缺少: {value}")
    for check in (
        "systemctl --quiet is-active display-manager.service || return 1",
        'pgrep -u "$uid" -x plasmashell >/dev/null || return 1',
        "qdbus6 org.kde.plasmashell /PlasmaShell org.freedesktop.DBus.Peer.Ping >/dev/null 2>&1 || return 1",
    ):
        if check not in probe:
            raise ValueError(f"桌面就绪探针未失败关闭: {check}")
    for value in ("Number of Screens: [1-9]", "Enabled: 1", "OpenGL renderer string: llvmpipe"):
        if value not in shell_wrapper:
            raise ValueError(f"PlasmaShell 兼容启动器缺少: {value}")
    if "QT_QUICK_BACKEND=software" not in shell_wrapper:
        raise ValueError("PlasmaShell 未为 llvmpipe 提供软件 Qt Quick 回退")
    if "ExecStart=/usr/libexec/lc300a/start-plasmashell" not in shell_drop_in:
        raise ValueError("PlasmaShell 用户服务未使用兼容启动器")
    for value in ("virtio-pci", "KWIN_DRM_NO_AMS=1", "/usr/bin/kwin_wayland_wrapper"):
        if value not in kwin_wrapper:
            raise ValueError(f"KWin 兼容启动器缺少: {value}")
    if "ExecStart=/usr/libexec/lc300a/start-kwin-wayland --xwayland" not in kwin_drop_in:
        raise ValueError("KWin 用户服务未使用兼容启动器")
    qemu = (PROJECT_ROOT / "scripts/test/qemu-boot.sh").read_text(encoding="utf-8")
    for value in (
        "LC300A_DESKTOP_OK",
        "screendump",
        "validate_framebuffer.py",
        "FRAMEBUFFER_TIMEOUT_SECONDS:-120",
        "FRAMEBUFFER_STABILITY_SECONDS",
        "local cpu=qemu64",
        "-vga virtio",
    ):
        if value not in qemu:
            raise ValueError(f"QEMU 桌面测试缺少: {value}")
    motd = (OVERLAY / "etc/motd").read_text(encoding="utf-8")
    if "阶段 1" in motd or "不代表完整桌面系统" in motd:
        raise ValueError("登录欢迎信息仍描述过时的阶段 1 控制台体验")


def validate() -> None:
    validate_packages()
    validate_sddm()
    validate_plasma()
    validate_color_scheme()
    validate_audio()
    validate_assembled_assets()
    validate_readiness()


def main() -> int:
    try:
        validate()
    except (configparser.Error, KeyError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"[ERROR] 桌面契约校验失败: {error}", file=sys.stderr)
        return 1
    print("[OK] Plasma、SDDM、UI、声音策略与桌面就绪契约通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
