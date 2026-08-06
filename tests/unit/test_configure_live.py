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

    def test_capacity_requirements_are_shared_by_welcome_and_installer(self):
        requirements = self.product["requirements"]
        welcome = CONFIGURE.welcome_qml(self.product)
        installer = CONFIGURE.calamares_welcome_config(self.product)
        for key in (
            "minimum_storage_gib",
            "recommended_storage_gib",
            "minimum_memory_gib",
            "typical_install_gib",
        ):
            self.assertIn(str(requirements[key]), welcome)
        for key in (
            "minimum_storage_gib",
            "recommended_storage_gib",
            "minimum_memory_gib",
        ):
            self.assertIn(f'"{requirements[key]} GiB"', welcome)
        self.assertIn(f'"约 " + "{requirements["typical_install_gib"]} GiB"', welcome)
        self.assertIn(
            f'requiredStorage:    {requirements["minimum_storage_gib"]}', installer
        )
        self.assertIn(
            f'requiredRam:        {requirements["minimum_memory_gib"]:.1f}', installer
        )

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
        for option in (
            "--mirror-bootstrap",
            "--mirror-chroot",
            "--mirror-binary",
            "--mirror-chroot-volatile",
            "--mirror-binary-volatile",
            "--parent-mirror-bootstrap",
            "--parent-mirror-chroot",
            "--parent-mirror-binary",
            "--parent-mirror-chroot-volatile",
            "--parent-mirror-binary-volatile",
        ):
            self.assertEqual(
                arguments[arguments.index(option) + 1],
                "http://mirrors.tuna.tsinghua.edu.cn/debian",
            )
        for option in (
            "--mirror-chroot-security",
            "--mirror-binary-security",
            "--parent-mirror-chroot-security",
            "--parent-mirror-binary-security",
        ):
            self.assertEqual(
                arguments[arguments.index(option) + 1],
                "http://mirrors.tuna.tsinghua.edu.cn/debian-security",
            )

    def test_arguments_only_configure_cross_version_rootfs_options(self):
        arguments = CONFIGURE.live_build_arguments(self.product)
        self.assertEqual(
            arguments[arguments.index("--apt-source-archives") + 1], "false"
        )
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
                "deb http://mirrors.tuna.tsinghua.edu.cn/debian-security trixie-security "
                "main contrib non-free-firmware\n",
            )
            binary_security = security.with_suffix(".binary")
            self.assertEqual(binary_security.read_text(), security.read_text())
            live_sources = (
                workspace / "config/includes.chroot/etc/apt/sources.list"
            ).read_text(encoding="utf-8")
            self.assertEqual(
                live_sources,
                "deb http://mirrors.tuna.tsinghua.edu.cn/debian trixie "
                "main contrib non-free-firmware\n"
                "deb http://mirrors.tuna.tsinghua.edu.cn/debian trixie-updates "
                "main contrib non-free-firmware\n",
            )
            self.assertNotIn("ftp.debian.org", live_sources)
            self.assertNotIn("deb-src", live_sources)
            installed_sources = (
                workspace
                / "config/includes.chroot/usr/share/calamares/helpers/lc300a-configure"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "deb https://mirrors.tuna.tsinghua.edu.cn/debian trixie main ",
                installed_sources,
            )
            self.assertIn(
                "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security "
                "trixie-security main ",
                installed_sources,
            )
            self.assertNotIn("deb.debian.org", installed_sources)
            boot = workspace / "lc300a-boot"
            self.assertEqual((boot / "grub.cfg").read_text(), CONFIGURE.grub_config(self.product))
            modern_hook = workspace / "config/hooks/live/010-system-defaults.hook.chroot"
            legacy_hook = workspace / "config/hooks/010-system-defaults.hook.chroot"
            self.assertEqual(modern_hook.read_bytes(), legacy_hook.read_bytes())
            hook_text = modern_hook.read_text(encoding="utf-8")
            self.assertIn(
                "Acquire::IndexTargets::deb::DEP-11::DefaultEnabled=true",
                hook_text,
            )
            self.assertIn("appstreamcli refresh --force --source=os", hook_text)
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
                "usr/share/lc300a-welcome/Main.qml",
            ):
                self.assertTrue((overlay / relative).is_file(), relative)
            welcome = (overlay / "usr/share/lc300a-welcome/Main.qml").read_text(
                encoding="utf-8"
            )
            self.assertIn(self.product["product"]["display_name"], welcome)
            self.assertIn(self.product["product"]["version"], welcome)
            self.assertNotIn("@PRODUCT_", welcome)
            self.assertNotIn("@BRAND_", welcome)
            installer_welcome = (
                overlay / "etc/calamares/modules/welcome.conf"
            ).read_text(encoding="utf-8")
            self.assertEqual(
                installer_welcome,
                CONFIGURE.calamares_welcome_config(self.product),
            )


if __name__ == "__main__":
    unittest.main()
