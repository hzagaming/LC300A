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

    def test_requires_realistic_capacity_requirements(self):
        requirements = self.valid["requirements"]
        self.assertGreaterEqual(requirements["minimum_storage_gib"], 16)
        self.assertGreaterEqual(
            requirements["recommended_storage_gib"],
            requirements["minimum_storage_gib"],
        )
        self.assertGreaterEqual(requirements["minimum_memory_gib"], 2)
        self.assertLessEqual(
            requirements["typical_install_gib"],
            requirements["minimum_storage_gib"],
        )

        config = copy.deepcopy(self.valid)
        del config["requirements"]
        with self.assertRaises(ValueError):
            VALIDATOR.validate_config(config)

        self.assert_rejected("requirements", "minimum_storage_gib", 4)
        self.assert_rejected("requirements", "recommended_storage_gib", 8)
        self.assert_rejected("requirements", "minimum_memory_gib", 1)
        self.assert_rejected("requirements", "typical_install_gib", 0)
        self.assert_rejected("requirements", "minimum_storage_gib", True)


if __name__ == "__main__":
    unittest.main()
