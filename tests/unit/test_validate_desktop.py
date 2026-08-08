import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_desktop", PROJECT_ROOT / "scripts/test/validate_desktop.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
EXPERIENCE_SPEC = importlib.util.spec_from_file_location(
    "validate_experience", PROJECT_ROOT / "scripts/test/validate_experience.py"
)
EXPERIENCE_VALIDATOR = importlib.util.module_from_spec(EXPERIENCE_SPEC)
EXPERIENCE_SPEC.loader.exec_module(EXPERIENCE_VALIDATOR)


class ValidateDesktopTest(unittest.TestCase):
    def test_desktop_contract(self):
        VALIDATOR.validate()

    def test_welcome_layout_and_registration_contract(self):
        template = (PROJECT_ROOT / "apps/welcome/Main.qml.in").read_text(
            encoding="utf-8"
        )
        self.assertIn("minimumWidth: 800", template)
        self.assertIn("minimumHeight: 600", template)
        self.assertIn("onCurrentStepChanged", template)
        self.assertIn("previewPlayer.stop()", template)
        desktop = VALIDATOR.read_config(
            "usr/share/applications/lc300a-welcome.desktop"
        )["Desktop Entry"]
        self.assertEqual(desktop.get("categories"), "Settings;")

    def test_lightweight_apps_and_low_memory_profile(self):
        packages = set(
            (PROJECT_ROOT / "distro/package-lists/desktop.list.chroot")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        self.assertTrue(
            {
                "ark",
                "gwenview",
                "kamoso",
                "kate",
                "kcalc",
                "htop",
                "ripgrep",
                "systemd-zram-generator",
            }.issubset(packages)
        )
        qemu = (PROJECT_ROOT / "scripts/test/qemu-boot.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("LC300A_QEMU_MEMORY_MIB:-2048", qemu)
        self.assertIn("LC300A_APP_FILTER", qemu)
        self.assertIn("tcg,thread=multi,tb-size=256", qemu)
        for application in ("ark", "gwenview", "kamoso", "kate", "kcalc"):
            self.assertIn(f"test_application {application} ", qemu)
        for marker in (
            "LC300A_CLI_TOOLS",
            "LC300A_ZRAM_ACTIVE",
            "LC300A_BALOO_DISABLED",
        ):
            self.assertIn(marker, qemu)
        for command in (
            "curl --version",
            "wget --version",
            "htop --version",
            "git init -q",
            "/usr/bin/kate -b",
            "rsync -a",
            "tree --noreport",
            "zip -jq",
            "unzip -p",
            "lsof -p",
            "sudo journalctl _SYSTEMD_USER_UNIT=",
            "lc300a-e2e-kate.log",
        ):
            self.assertIn(command, qemu)

        welcome = (PROJECT_ROOT / "apps/welcome/Main.qml.in").read_text(
            encoding="utf-8"
        )
        for application in ("Kate", "KCalc", "Kamoso"):
            self.assertIn(application, welcome)

        motd = VALIDATOR.CONFIGURE.release_files(
            VALIDATOR.tomllib.loads(
                (PROJECT_ROOT / "branding/product.toml").read_text(encoding="utf-8")
            )
        )["etc/motd"]
        self.assertIn("Kate、KCalc、Kamoso", motd)
        self.assertIn("curl、wget、git、jq、htop、rg", motd)

    def test_installed_color_scheme_text_contrast(self):
        colors = VALIDATOR.read_config("usr/share/color-schemes/LuochuanFlow.colors")
        for section in ("Colors:Button", "Colors:Selection", "Colors:Tooltip", "Colors:View", "Colors:Window"):
            background = self.hex_color(colors[section]["BackgroundNormal"])
            for role, value in colors[section].items():
                if role.startswith("foreground"):
                    ratio = EXPERIENCE_VALIDATOR.contrast_ratio(self.hex_color(value), background)
                    self.assertGreaterEqual(ratio, 4.5, f"{section}.{role}: {ratio:.2f}:1")

    @staticmethod
    def hex_color(value: str) -> str:
        return "#" + "".join(f"{int(channel):02X}" for channel in value.split(","))


if __name__ == "__main__":
    unittest.main()
