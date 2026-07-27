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
