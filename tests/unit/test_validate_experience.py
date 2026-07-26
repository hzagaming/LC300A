import copy
import importlib.util
import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_experience", PROJECT_ROOT / "scripts/test/validate_experience.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ExperienceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.product = tomllib.loads(
            (PROJECT_ROOT / "branding/product.toml").read_text(encoding="utf-8")
        )
        cls.experience = tomllib.loads(
            (PROJECT_ROOT / "branding/experience.toml").read_text(encoding="utf-8")
        )
        cls.sound_theme = tomllib.loads(
            (PROJECT_ROOT / "branding/sounds/theme.toml").read_text(encoding="utf-8")
        )

    def test_black_white_contrast_is_twenty_one(self):
        self.assertAlmostEqual(VALIDATOR.contrast_ratio("#000000", "#FFFFFF"), 21.0)

    def test_current_palettes_pass(self):
        VALIDATOR.validate_contrast(self.product, self.experience)

    def test_rejects_low_text_contrast(self):
        product = copy.deepcopy(self.product)
        product["colors"]["light"]["text"] = product["colors"]["light"]["background"]
        with self.assertRaises(ValueError):
            VALIDATOR.validate_contrast(product, self.experience)

    def test_rejects_bgm_autoplay(self):
        experience = copy.deepcopy(self.experience)
        experience["audio"]["background_music_autoplay"] = True
        with self.assertRaises(ValueError):
            VALIDATOR.validate_policy(experience, self.sound_theme)

    def test_rejects_small_touch_targets(self):
        experience = copy.deepcopy(self.experience)
        experience["layout"]["touch_target_px"] = 32
        with self.assertRaises(ValueError):
            VALIDATOR.validate_policy(experience, self.sound_theme)


if __name__ == "__main__":
    unittest.main()
