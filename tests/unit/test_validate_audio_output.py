import importlib.util
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_audio_output", PROJECT_ROOT / "scripts/test/validate_audio_output.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ValidateAudioOutputTest(unittest.TestCase):
    def write_wav(self, directory: str, samples: list[int]) -> Path:
        path = Path(directory) / "audio.wav"
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
        return path

    def test_accepts_audible_pcm(self):
        with tempfile.TemporaryDirectory() as directory:
            samples = [0, 4000, -4000, 1000] * 4000
            VALIDATOR.validate(self.write_wav(directory, samples), 0.5, 256)

    def test_rejects_silent_pcm(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                VALIDATOR.validate(self.write_wav(directory, [0] * 8000), 0.5, 256)

    def test_rejects_short_pcm(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                VALIDATOR.validate(self.write_wav(directory, [1000] * 100), 0.5, 256)

    def test_accepts_qemu_streaming_wav_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_wav(directory, [0, 4000, -4000, 1000] * 4000)
            content = bytearray(path.read_bytes())
            content[4:8] = bytes(4)
            content[40:44] = bytes(4)
            path.write_bytes(content)
            VALIDATOR.validate(path, 0.5, 256)

    def test_rejects_incomplete_pcm_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_wav(directory, [0, 4000, -4000, 1000] * 4000)
            content = bytearray(path.read_bytes())
            content[4:8] = bytes(4)
            content[40:44] = bytes(4)
            path.write_bytes(content + b"\x01")
            with self.assertRaises(ValueError):
                VALIDATOR.validate(path, 0.5, 256)

    def test_rejects_excessive_active_audio_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_wav(directory, [1000] * 8000)
            with self.assertRaises(ValueError):
                VALIDATOR.validate(path, 0.5, 256, 0.5)


if __name__ == "__main__":
    unittest.main()
