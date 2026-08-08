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
        "ark",
        "curl",
        "dolphin",
        "firefox-esr",
        "flatpak",
        "fonts-noto-cjk",
        "git",
        "gwenview",
        "htop",
        "jq",
        "kamoso",
        "kate",
        "kcalc",
        "konsole",
        "kwin-wayland",
        "lsof",
        "network-manager",
        "packagekit",
        "pipewire-pulse",
        "plasma-desktop",
        "plasma-discover",
        "plasma-discover-backend-flatpak",
        "plasma-nm",
        "plasma-pa",
        "plasma-workspace",
        "python3",
        "qml-qt6",
        "ripgrep",
        "rsync",
        "sddm",
        "sddm-theme-breeze",
        "systemd-zram-generator",
        "systemsettings",
        "tree",
        "unzip",
        "wireplumber",
        "wget",
        "xwayland",
        "zip",
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
    if general.get("background") != "/usr/share/wallpapers/LC300AFlow/contents/images_dark/3840x2160.svg":
        raise ValueError("SDDM 背景未使用 LC300A 深色壁纸")
    if general.get("logo") != "/usr/share/pixmaps/lc300a-mark.svg" or general.get("showlogo") != "shown":
        raise ValueError("SDDM Logo 配置错误")
    foreground = general.get("color")
    dark = product["colors"]["dark"]
    minimum = tomllib.loads((BRANDING / "experience.toml").read_text(encoding="utf-8"))[
        "accessibility"
    ]["minimum_text_contrast"]
    if foreground != dark["text"]:
        raise ValueError("SDDM 前景色未使用深色主题文本色")
    if EXPERIENCE_VALIDATOR.contrast_ratio(foreground, dark["background"]) < minimum:
        raise ValueError("SDDM 登录文本对比度不足")


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
        "lc300a-installer.desktop",
        "lc300a-welcome.desktop",
        "firefox-esr.desktop",
        "org.kde.discover.desktop",
        "org.kde.dolphin.desktop",
        "org.kde.konsole.desktop",
        "org.kde.kate.desktop",
        "org.kde.kcalc.desktop",
        "org.kde.kamoso.desktop",
    ]
    if favorites.get("prepend", "").split(";") != expected:
        raise ValueError("应用菜单未固定核心应用和轻量工具")
    if favorites.getboolean("ignoredefaults", fallback=True):
        raise ValueError("应用菜单不应隐藏 Plasma 默认收藏")

    baloo = read_config("etc/xdg/baloofilerc")["Basic Settings"]
    if baloo.getboolean("Indexing-Enabled", fallback=True):
        raise ValueError("低资源默认配置仍启用 Baloo 文件索引")

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


def validate_welcome() -> None:
    product = tomllib.loads((BRANDING / "product.toml").read_text(encoding="utf-8"))
    template = (PROJECT_ROOT / "apps/welcome/Main.qml.in").read_text(encoding="utf-8")
    for value in (
        "import QtQuick",
        "import QtQuick.Controls",
        "import QtQuick.Layouts",
        "import QtMultimedia",
        'Qt.openUrlExternally("lc300a-action:" + name)',
        'Qt.openUrlExternally("lc300a-action:finish")',
        "/usr/share/sounds/luochuan-flow/stereo/desktop-login.wav",
        "/usr/share/sounds/luochuan-flow/preview/ambient-preview.wav",
        "onClosing: previewPlayer.stop()",
        "minimumWidth: 800",
        "minimumHeight: 600",
        "onCurrentStepChanged",
        'previewPlayer.source = ""',
        "columns: 2",
    ):
        if value not in template:
            raise ValueError(f"欢迎程序缺少: {value}")
    if "autoPlay" in template:
        raise ValueError("欢迎程序声音不得自动播放")

    action = (OVERLAY / "usr/local/bin/lc300a-welcome-action").read_text(encoding="utf-8")
    for value in (
        "lc300a-action:settings)",
        "lc300a-action:apps)",
        "lc300a-action:finish)",
        "umask 077",
        'mktemp "$state_root/.welcome-complete.XXXXXX"',
        'chmod 0600 "$state_temp"',
        'mv "$state_temp" "$state_root/welcome-complete"',
    ):
        if value not in action:
            raise ValueError(f"欢迎程序动作 helper 缺少: {value}")
    if action.count("lc300a-action:") != 3 or "Unsupported LC300A welcome action" not in action:
        raise ValueError("欢迎程序动作 helper 未严格限制 URI 白名单")

    launcher = (OVERLAY / "usr/local/bin/lc300a-welcome").read_text(encoding="utf-8")
    for value in (
        "--first-login)",
        "/run/live/medium",
        "welcome-complete",
        "/usr/lib/qt6/bin/qml",
        "/usr/share/lc300a-welcome/Main.qml",
        "qdbus6 org.kde.plasmashell /PlasmaShell org.freedesktop.DBus.Peer.Ping",
        '"$attempt" -lt 120',
        "pgrep -x ksplashqml",
    ):
        if value not in launcher:
            raise ValueError(f"欢迎程序启动器缺少: {value}")

    desktop = read_config("usr/share/applications/lc300a-welcome.desktop")["Desktop Entry"]
    if desktop.get("exec") != "/usr/local/bin/lc300a-welcome" or desktop.getboolean(
        "terminal", fallback=True
    ):
        raise ValueError("欢迎程序菜单入口错误")
    if desktop.get("categories") != "Settings;":
        raise ValueError("欢迎程序菜单必须只注册一个主分类")
    action_desktop = read_config(
        "usr/share/applications/lc300a-welcome-action.desktop"
    )["Desktop Entry"]
    if action_desktop.get("mimetype") != "x-scheme-handler/lc300a-action;" or not action_desktop.getboolean(
        "nodisplay", fallback=False
    ):
        raise ValueError("欢迎程序 URI handler 注册错误")
    autostart = read_config("etc/xdg/autostart/lc300a-welcome.desktop")["Desktop Entry"]
    if autostart.get("exec") != "/usr/local/bin/lc300a-welcome --first-login" or autostart.get(
        "onlyshowin"
    ) != "KDE;":
        raise ValueError("欢迎程序首次登录启动配置错误")

    for relative in ("usr/local/bin/lc300a-welcome", "usr/local/bin/lc300a-welcome-action"):
        if not (OVERLAY / relative).stat().st_mode & 0o100:
            raise ValueError(f"欢迎程序脚本不可执行: {relative}")
    hook = (PROJECT_ROOT / "distro/hooks/010-system-defaults.hook.chroot").read_text(
        encoding="utf-8"
    )
    if "update-desktop-database /usr/share/applications" not in hook:
        raise ValueError("欢迎程序 URI handler 缓存未在构建时更新")

    rendered = CONFIGURE.welcome_qml(product)
    for value in (
        product["product"]["display_name"],
        product["product"]["version"],
        product["identity"]["support_url"],
        str(product["requirements"]["minimum_storage_gib"]),
        str(product["requirements"]["recommended_storage_gib"]),
        str(product["requirements"]["minimum_memory_gib"]),
        str(product["requirements"]["typical_install_gib"]),
    ):
        if value not in rendered:
            raise ValueError(f"欢迎程序未渲染产品值: {value}")
    for placeholder in (
        "@PRODUCT_DISPLAY_NAME@",
        "@PRODUCT_VERSION@",
        "@SUPPORT_URL@",
        "@BRAND_",
    ):
        if placeholder in rendered:
            raise ValueError(f"欢迎程序仍含未解析占位符: {placeholder}")


def validate_firefox() -> None:
    preferences = (
        OVERLAY / "etc/firefox-esr/lc300a.js"
    ).read_text(encoding="utf-8")
    for value in (
        'pref("browser.aboutwelcome.enabled", false);',
        'pref("startup.homepage_welcome_url", "");',
        'pref("startup.homepage_welcome_url.additional", "");',
        'pref("datareporting.policy.dataSubmissionEnabled", false);',
    ):
        if value not in preferences:
            raise ValueError(f"Firefox 首次启动配置缺少: {value}")


def validate_assembled_assets() -> None:
    expected = {
        "usr/share/pixmaps/lc300a-mark.svg",
        "usr/share/wallpapers/LC300AFlow/contents/images/3840x2160.svg",
        "usr/share/wallpapers/LC300AFlow/contents/images_dark/3840x2160.svg",
        "usr/share/sounds/luochuan-flow/stereo/desktop-login.wav",
        "usr/share/sounds/luochuan-flow/stereo/dialog-warning.wav",
        "usr/share/sounds/luochuan-flow/stereo/message-new-instant.wav",
        "usr/share/sounds/luochuan-flow/preview/ambient-preview.wav",
        "usr/share/lc300a-welcome/Main.qml",
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
    discover = (OVERLAY / "usr/local/bin/plasma-discover").read_text(encoding="utf-8")
    for value in (
        "/usr/bin/plasma-discover",
        "--listbackends",
        "--backends|--backends=*",
        "backends=packagekit-backend",
        "flatpak remotes --system --columns=name",
        "flatpak remotes --user --columns=name",
        'backends="$backends,flatpak-backend"',
        '--backends "$backends"',
    ):
        if value not in discover:
            raise ValueError(f"Discover 安全启动器缺少: {value}")
    qemu = (PROJECT_ROOT / "scripts/test/qemu-boot.sh").read_text(encoding="utf-8")
    for value in (
        "LC300A_DESKTOP_OK",
        "screendump",
        "validate_framebuffer.py",
        "FRAMEBUFFER_TIMEOUT_SECONDS:-120",
        "FRAMEBUFFER_STABILITY_SECONDS",
        "APP_LAUNCH_TIMEOUT_SECONDS",
        "APP_SETTLE_SECONDS:-30",
        "serial-console.py",
        "SERIAL_SOCKET",
        "systemd-run --user",
        "systemctl --user is-active",
        "firefox-esr",
        "dolphin --new-window",
        "/usr/bin/systemsettings",
        "/usr/bin/ark",
        "/usr/bin/gwenview",
        "/usr/bin/kamoso",
        "/usr/bin/kate -b",
        "/usr/bin/kcalc",
        "/usr/local/bin/lc300a-welcome",
        "xdg-mime query default x-scheme-handler/lc300a-action",
        "xdg-open lc300a-action:finish",
        "plasma-discover",
        "https://example.com",
        "apps-firefox-page.ppm",
        "apps-welcome-step$step.ppm",
        "urllib.request",
        "LC300A_FIREFOX_NETWORK",
        "LC300A_CLI_TOOLS",
        "LC300A_ZRAM_ACTIVE",
        "LC300A_BALOO_DISABLED",
        "--new-window https://example.com",
        "ich9-intel-hda",
        "hda-output,audiodev=audio0",
        "quit_qemu",
        'connection.sendall(b"quit\\n")',
        "validate_audio_output.py",
        "--minimum-change-ratio 0.15",
        "--minimum-content-dark-ratio 0.002",
        "--minimum-content-colors 32",
        "--minimum-content-chroma-ratio 0.02",
        "--maximum-change-ratio 0.05",
        "--maximum-active-duration 2.25",
        "--minimum-active-duration 2.5",
        "自动会话音效有效且未检测到自动 BGM",
        "local cpu=qemu64",
        "LC300A_QEMU_MEMORY_MIB:-2048",
        "LC300A_QEMU_CPUS:-6",
        "tcg,thread=multi,tb-size=256",
        "virtio-vga,xres=1280,yres=800",
    ):
        if value not in qemu:
            raise ValueError(f"QEMU 桌面测试缺少: {value}")
    if "-m 4096" in qemu or "-vga virtio" in qemu:
        raise ValueError("QEMU 仍使用旧的高内存或隐式显示配置")
    if "enter_firefox_url" in qemu:
        raise ValueError("Firefox 联网测试仍使用不可靠的 QEMU 逐键网址输入")
    if "--new-tab https://example.com" in qemu:
        raise ValueError("Firefox E2E 不得重复打开相同页面标签")
    if "/usr/local/bin/plasma-discover --backends packagekit-backend" in qemu:
        raise ValueError("Discover E2E 必须验证发行版默认后端选择逻辑")
    serial_bridge = qemu.split("start_serial_bridge() {", 1)[1].split("\n}", 1)[0]
    if 'rm -f -- "$SERIAL_SOCKET"' in serial_bridge:
        raise ValueError("串口桥不得删除由 QEMU 持有的串口 socket")
    if 'local restored="$PROJECT_ROOT/build/artifacts/apps-$name-restored.ppm"' not in qemu:
        raise ValueError("图形应用测试缺少独立的桌面恢复截图")
    product = tomllib.loads((BRANDING / "product.toml").read_text(encoding="utf-8"))
    motd = CONFIGURE.release_files(product)["etc/motd"]
    for value in (
        product["product"]["version"],
        "Plasma Wayland",
        "Firefox ESR",
        "Discover",
        "Calamares 图形安装器",
        "Kate、KCalc、Kamoso",
        "curl、wget、git、jq、htop、rg",
    ):
        if value not in motd:
            raise ValueError(f"登录欢迎信息缺少: {value}")


def validate() -> None:
    validate_packages()
    validate_sddm()
    validate_plasma()
    validate_color_scheme()
    validate_audio()
    validate_welcome()
    validate_firefox()
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
