import importlib.util
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "repository_hygiene", PROJECT_ROOT / "scripts/test/repository_hygiene.py"
)
HYGIENE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HYGIENE)


class RepositoryHygieneTest(unittest.TestCase):
    def inspect_files(self, files):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return HYGIENE.inspect_repository(root)[0]

    def test_accepts_normal_source(self):
        self.assertEqual(self.inspect_files({"README.md": "# Project\n"}), [])

    def test_rejects_environment_file(self):
        self.assertTrue(self.inspect_files({".env": "TOKEN=value\n"}))

    def test_rejects_runtime_directory(self):
        self.assertTrue(self.inspect_files({"__pycache__/module.pyc.txt": "cache\n"}))

    def test_rejects_runtime_directory_inside_source_build_module(self):
        self.assertTrue(
            self.inspect_files({"scripts/build/__pycache__/module.pyc.txt": "cache\n"})
        )

    def test_ignores_root_build_artifacts(self):
        self.assertEqual(self.inspect_files({"build/generated.iso": "artifact\n"}), [])

    def test_rejects_private_key_content(self):
        key_header = "-----BEGIN " + "PRIVATE KEY-----\n"
        self.assertTrue(self.inspect_files({"secret.txt": key_header}))


if __name__ == "__main__":
    unittest.main()
