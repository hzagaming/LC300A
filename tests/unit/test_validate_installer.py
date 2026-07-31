#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_installer", PROJECT_ROOT / "scripts/test/validate_installer.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class InstallerValidationTests(unittest.TestCase):
    def test_installer_contract(self):
        VALIDATOR.validate()


if __name__ == "__main__":
    unittest.main()
