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

    def test_accepts_meaningful_framebuffer_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = self.write_ppm(directory, 64, 48, bytes((32, 64, 96)) * 64 * 48)
            candidate = Path(directory) / "candidate.ppm"
            candidate.write_bytes(
                b"P6\n64 48\n255\n"
                + bytes((32, 64, 96)) * 32 * 48
                + bytes((220, 220, 220)) * 32 * 48
            )
            VALIDATOR.validate_transition(reference, candidate, 0.1)

    def test_rejects_unchanged_framebuffer_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            pixels = bytes((32, 64, 96)) * 64 * 48
            reference = self.write_ppm(directory, 64, 48, pixels)
            candidate = Path(directory) / "candidate.ppm"
            candidate.write_bytes(b"P6\n64 48\n255\n" + pixels)
            with self.assertRaises(ValueError):
                VALIDATOR.validate_transition(reference, candidate, 0.1)

    def test_rejects_framebuffer_that_did_not_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = self.write_ppm(directory, 64, 48, bytes((32, 64, 96)) * 64 * 48)
            candidate = Path(directory) / "candidate.ppm"
            candidate.write_bytes(b"P6\n64 48\n255\n" + bytes((220, 220, 220)) * 64 * 48)
            with self.assertRaises(ValueError):
                VALIDATOR.validate_restoration(reference, candidate, 0.02)

    def test_accepts_visible_content_in_central_viewport(self):
        with tempfile.TemporaryDirectory() as directory:
            pixels = bytearray(bytes((248, 248, 248)) * 64 * 48)
            for y in range(12, 36):
                for x in range(20, 44):
                    offset = (y * 64 + x) * 3
                    pixels[offset : offset + 3] = bytes((32, 32, 32))
            path = self.write_ppm(directory, 64, 48, bytes(pixels))
            VALIDATOR.validate_content_region(path, 0.002)

    def test_rejects_blank_central_viewport(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_ppm(directory, 64, 48, bytes((248, 248, 248)) * 64 * 48)
            with self.assertRaises(ValueError):
                VALIDATOR.validate_content_region(path, 0.002)


if __name__ == "__main__":
    unittest.main()
