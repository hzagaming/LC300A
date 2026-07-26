import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "build_manifest", PROJECT_ROOT / "scripts/build/build_manifest.py"
)
MANIFEST = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MANIFEST)


class BuildManifestTest(unittest.TestCase):
    def test_manifest_records_iso_and_packages(self):
        responses = {
            ("git", "rev-parse", "HEAD"): "a" * 40,
            ("git", "status", "--porcelain"): "",
            ("git", "show", "-s", "--format=%ct", "a" * 40): "1700000000",
            ("lb", "--version"): "live-build test",
        }
        original = MANIFEST.command
        MANIFEST.command = lambda *arguments: responses[arguments]
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                iso = root / "LC300A-x86_64.iso"
                packages = root / "package-manifest.txt"
                iso.write_bytes(b"lc300a-iso")
                packages.write_text("bash\t1\nlinux-image-amd64\t1\n", encoding="utf-8")
                result = MANIFEST.create_manifest(iso, packages)
        finally:
            MANIFEST.command = original

        self.assertEqual(result["package_count"], 2)
        self.assertEqual(result["git_dirty"], False)
        self.assertEqual(result["iso"]["bytes"], 10)
        self.assertEqual(result["iso"]["sha256"], hashlib.sha256(b"lc300a-iso").hexdigest())


if __name__ == "__main__":
    unittest.main()
