import copy
import importlib.util
import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_product", PROJECT_ROOT / "scripts/test/validate_product.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ProductConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = tomllib.loads(
            (PROJECT_ROOT / "branding/product.toml").read_text(encoding="utf-8")
        )

    def assert_rejected(self, section, key, value):
        config = copy.deepcopy(self.valid)
        config[section][key] = value
        with self.assertRaises(ValueError):
            VALIDATOR.validate_config(config)

    def test_current_config_is_valid(self):
        self.assertEqual(VALIDATOR.validate_config(copy.deepcopy(self.valid)), self.valid)

    def test_rejects_invalid_version(self):
        self.assert_rejected("product", "version_id", "01.0.0")

    def test_rejects_wrong_base_system(self):
        self.assert_rejected("base", "suite", "unstable")

    def test_rejects_root_live_user(self):
        self.assert_rejected("identity", "live_user", "root")

    def test_rejects_unsafe_output_path(self):
        self.assert_rejected("artifacts", "output_directory", "../artifacts")

    def test_rejects_url_credentials(self):
        self.assert_rejected("identity", "home_url", "https://user@example.com/lc300a")

    def test_rejects_invalid_color(self):
        config = copy.deepcopy(self.valid)
        config["colors"]["light"]["primary"] = "blue"
        with self.assertRaises(ValueError):
            VALIDATOR.validate_config(config)


if __name__ == "__main__":
    unittest.main()
