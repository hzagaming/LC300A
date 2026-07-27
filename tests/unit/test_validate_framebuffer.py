import importlib.util
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_framebuffer", PROJECT_ROOT / "scripts/test/validate_framebuffer.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ValidateFramebufferTest(unittest.TestCase):
    def write_ppm(self, directory: str, width: int, height: int, pixels: bytes) -> Path:
        path = Path(directory) / "screen.ppm"
        path.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + pixels)
        return path

    def test_accepts_varied_framebuffer(self):
        with tempfile.TemporaryDirectory() as directory:
            pixels = bytes(
                channel
                for index in range(64 * 48)
                for channel in (index % 251, (index * 3) % 251, (index * 7) % 251)
            )
            VALIDATOR.validate(self.write_ppm(directory, 64, 48, pixels), 64, 48)

    def test_rejects_uniform_framebuffer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_ppm(directory, 64, 48, b"\0" * 64 * 48 * 3)
            with self.assertRaises(ValueError):
                VALIDATOR.validate(path, 64, 48)

    def test_rejects_window_drawn_over_black_background(self):
        with tempfile.TemporaryDirectory() as directory:
            black = b"\0" * 48 * 48 * 3
            window = bytes(
                channel
                for index in range(16 * 48)
                for channel in (64 + index % 191, 96 + index % 159, 128 + index % 127)
            )
            path = self.write_ppm(directory, 64, 48, black + window)
            with self.assertRaises(ValueError):
                VALIDATOR.validate(path, 64, 48)


if __name__ == "__main__":
    unittest.main()
