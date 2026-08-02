import copy
import importlib.util
import tempfile
import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "configure_live", PROJECT_ROOT / "scripts/build/configure_live.py"
)
CONFIGURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONFIGURE)


class ConfigureLiveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product = tomllib.loads(
            (PROJECT_ROOT / "branding/product.toml").read_text(encoding="utf-8")
        )

    def test_release_quoting_escapes_shell_expansion(self):
        self.assertEqual(CONFIGURE.quote_release('a"b$c`d\\e'), '"a\\"b\\$c\\`d\\\\e"')

    def test_release_files_describe_current_graphical_experience(self):
        motd = CONFIGURE.release_files(self.product)["etc/motd"]
        for value in (
            self.product["product"]["version"],
            "Plasma Wayland",
            "Firefox ESR",
            "Discover",
            "Calamares 图形安装器",
        ):
            self.assertIn(value, motd)

    def test_arguments_use_product_identity(self):
        arguments = CONFIGURE.live_build_arguments(self.product)
        boot_parameters = arguments[arguments.index("--bootappend-live") + 1]
        self.assertIn("username=lc300a-live", boot_parameters)
        for parameter in (
            "quiet",
            "splash",
            "plymouth.ignore-serial-consoles",
            "systemd.unit=graphical.target",
            "systemd.show_status=auto",
        ):
            self.assertIn(parameter, boot_parameters)
        self.assertEqual(arguments[arguments.index("--distribution") + 1], "trixie")

    def test_arguments_only_configure_cross_version_rootfs_options(self):
        arguments = CONFIGURE.live_build_arguments(self.product)
        self.assertEqual(arguments[arguments.index("--security") + 1], "false")
        self.assertEqual(arguments[arguments.index("--firmware-chroot") + 1], "false")
        self.assertEqual(arguments[arguments.index("--firmware-binary") + 1], "false")
        self.assertEqual(arguments[arguments.index("--initsystem") + 1], "systemd")
        self.assertNotIn("--bootloaders", arguments)
        self.assertNotIn("--bootloader", arguments)
        self.assertNotIn("--updates", arguments)
        self.assertNotIn("--image-name", arguments)

    def test_grub_config_boots_live_rootfs(self):
        config = CONFIGURE.grub_config(self.product)
        self.assertIn("linux /live/vmlinuz", config)
        self.assertIn("initrd /live/initrd.img", config)
        self.assertIn("username=lc300a-live", config)
        self.assertIn("console=ttyS0,115200n8", config)
        self.assertIn('menuentry "落川OS 300型 Live (图形桌面)"', config)
        self.assertIn('menuentry "落川OS 300型 Live (纯文字模式)"', config)
        graphical, console = config.split('menuentry "落川OS 300型 Live (纯文字模式)"', 1)
        self.assertIn("systemd.unit=graphical.target", graphical)
        self.assertIn(" quiet ", graphical)
        self.assertIn(" splash ", graphical)
        self.assertIn("systemd.unit=multi-user.target", console)
        self.assertNotIn(" quiet ", console)
        self.assertNotIn(" splash ", console)

    def test_rejects_wrong_base(self):
        product = copy.deepcopy(self.product)
        product["base"]["suite"] = "unstable"
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            original = CONFIGURE.product_config
            CONFIGURE.product_config = lambda: product
            try:
                CONFIGURE.configure(Path(directory), False)
            finally:
                CONFIGURE.product_config = original

    def test_assemble_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            CONFIGURE.configure(workspace, False)
            stale = workspace / "config/includes.chroot/stale"
            stale.write_text("stale", encoding="utf-8")
            CONFIGURE.configure(workspace, False)
            self.assertFalse(stale.exists())
            security = workspace / "config/archives/lc300a-security.list.chroot"
            self.assertEqual(
                security.read_text(encoding="utf-8"),
                "deb http://security.debian.org/debian-security trixie-security "
                "main contrib non-free-firmware\n",
            )
            binary_security = security.with_suffix(".binary")
            self.assertEqual(binary_security.read_text(), security.read_text())
            boot = workspace / "lc300a-boot"
            self.assertEqual((boot / "grub.cfg").read_text(), CONFIGURE.grub_config(self.product))
            modern_hook = workspace / "config/hooks/live/010-system-defaults.hook.chroot"
            legacy_hook = workspace / "config/hooks/010-system-defaults.hook.chroot"
            self.assertEqual(modern_hook.read_bytes(), legacy_hook.read_bytes())
            self.assertTrue(modern_hook.stat().st_mode & 0o100)
            self.assertTrue(legacy_hook.stat().st_mode & 0o100)
            overlay = workspace / "config/includes.chroot"
            for relative in (
                "etc/plymouth/plymouthd.conf",
                "etc/xdg/kscreenlockerrc",
                "etc/xdg/kicker-extra-favoritesrc",
                "etc/xdg/powerdevilrc",
                "usr/local/bin/plasma-discover",
                "usr/share/pixmaps/lc300a-mark.svg",
                "usr/share/plymouth/themes/lc300a/lc300a-mark.png",
                "usr/share/plymouth/themes/lc300a/lc300a.plymouth",
                "usr/share/plymouth/themes/lc300a/lc300a.script",
                "usr/share/wallpapers/LC300AFlow/contents/images/3840x2160.svg",
                "usr/share/wallpapers/LC300AFlow/contents/images_dark/3840x2160.svg",
                "usr/share/sounds/luochuan-flow/stereo/desktop-login.wav",
                "usr/share/sounds/luochuan-flow/preview/ambient-preview.wav",
            ):
                self.assertTrue((overlay / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
