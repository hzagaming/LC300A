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

    def test_arguments_use_product_identity(self):
        arguments = CONFIGURE.live_build_arguments(self.product)
        boot_parameters = arguments[arguments.index("--bootappend-live") + 1]
        self.assertIn("username=lc300a-live", boot_parameters)
        self.assertEqual(arguments[arguments.index("--distribution") + 1], "trixie")

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


if __name__ == "__main__":
    unittest.main()
