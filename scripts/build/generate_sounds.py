#!/usr/bin/env python3

import argparse
import hashlib
import json
import math
import struct
import tempfile
import tomllib
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
THEME_PATH = PROJECT_ROOT / "branding/sounds/theme.toml"
OUTPUT_PATH = PROJECT_ROOT / "branding/sounds"


def smooth(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def add_tone(
    samples: list[float],
    sample_rate: int,
    frequency: float,
    start: float,
    duration: float,
    amplitude: float,
    attack: float = 0.04,
    release: float = 0.12,
    phase: float = 0.0,
) -> None:
    start_frame = max(0, round(start * sample_rate))
    frame_count = min(round(duration * sample_rate), len(samples) - start_frame)
    attack_frames = max(1, round(attack * sample_rate))
    release_frames = max(1, round(release * sample_rate))

    for index in range(frame_count):
        envelope = min(
            smooth(index / attack_frames),
            smooth((frame_count - 1 - index) / release_frames),
        )
        time = index / sample_rate
        samples[start_frame + index] += amplitude * envelope * math.sin(
            2.0 * math.pi * frequency * time + phase
        )


def compose(sound_id: str, duration: float, sample_rate: int, peak_limit: float) -> list[float]:
    samples = [0.0] * round(duration * sample_rate)
    if sound_id == "startup":
        add_tone(samples, sample_rate, 293.66, 0.00, 1.25, 0.24, 0.16, 0.42)
        add_tone(samples, sample_rate, 440.00, 0.22, 1.30, 0.19, 0.14, 0.44)
        add_tone(samples, sample_rate, 659.25, 0.54, 1.18, 0.14, 0.12, 0.5)
        add_tone(samples, sample_rate, 880.00, 0.82, 0.82, 0.07, 0.08, 0.44)
    elif sound_id == "notification":
        add_tone(samples, sample_rate, 587.33, 0.00, 0.30, 0.28, 0.02, 0.13)
        add_tone(samples, sample_rate, 880.00, 0.10, 0.30, 0.20, 0.02, 0.15)
    elif sound_id == "warning":
        add_tone(samples, sample_rate, 392.00, 0.00, 0.34, 0.23, 0.03, 0.14)
        add_tone(samples, sample_rate, 293.66, 0.22, 0.36, 0.25, 0.03, 0.16)
    elif sound_id == "ambient":
        for frequency, amplitude, phase in (
            (146.83, 0.13, 0.0),
            (220.00, 0.10, math.pi / 3.0),
            (329.63, 0.07, math.pi / 2.0),
        ):
            add_tone(samples, sample_rate, frequency, 0.0, duration, amplitude, 1.2, 1.4, phase)
        for start, frequency in ((1.0, 587.33), (2.7, 659.25), (4.4, 440.00), (5.9, 587.33)):
            add_tone(samples, sample_rate, frequency, start, 1.15, 0.055, 0.22, 0.48)
    else:
        raise ValueError(f"unknown sound id: {sound_id}")

    peak = max(abs(sample) for sample in samples)
    if peak:
        scale = min(1.0, peak_limit / peak)
        samples = [sample * scale for sample in samples]
    return samples


def write_wave(path: Path, samples: list[float], sample_rate: int) -> dict:
    frames = b"".join(
        struct.pack("<h", round(max(-1.0, min(1.0, sample)) * 32767)) for sample in samples
    )
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(frames)
    content = path.read_bytes()
    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "frames": len(samples),
        "peak": round(max(abs(sample) for sample in samples), 6),
    }


def generate(output_path: Path) -> None:
    config = tomllib.loads(THEME_PATH.read_text(encoding="utf-8"))
    sample_rate = config["format"]["sample_rate"]
    peak_limit = config["format"]["peak_limit"]
    if config["format"]["channels"] != 1 or config["format"]["sample_width_bits"] != 16:
        raise ValueError("sound generator supports mono 16-bit PCM only")
    output_path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "theme": config["theme"]["id"],
        "license": config["theme"]["license"],
        "sample_rate": sample_rate,
        "channels": config["format"]["channels"],
        "sample_width_bits": config["format"]["sample_width_bits"],
        "files": [],
    }
    for sound_id, sound in config["sounds"].items():
        duration = sound["duration_ms"] / 1000.0
        path = output_path / sound["file"]
        metadata = write_wave(
            path,
            compose(sound_id, duration, sample_rate, peak_limit),
            sample_rate,
        )
        manifest["files"].append(
            {
                "id": sound_id,
                "file": sound["file"],
                "duration_ms": sound["duration_ms"],
                **metadata,
            }
        )
    (output_path / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def check() -> None:
    with tempfile.TemporaryDirectory(prefix="lc300a-sounds-") as directory:
        generated = Path(directory)
        generate(generated)
        expected_files = {path.name for path in generated.iterdir()}
        actual_files = {"manifest.json", *(path.name for path in OUTPUT_PATH.glob("*.wav"))}
        if actual_files != expected_files:
            raise SystemExit("[ERROR] 声音目录包含缺失或遗留的生成资产")
        for name in expected_files:
            expected = (OUTPUT_PATH / name).read_bytes()
            actual = (generated / name).read_bytes()
            if expected != actual:
                raise SystemExit(f"[ERROR] 声音资产需要重新生成: {name}")
    print(f"[OK] 声音资产可复现（{len(expected_files) - 1} 个 WAV）")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic LC300A sound assets")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if arguments.check:
        check()
    else:
        generate(OUTPUT_PATH)
        print(f"[OK] 声音资产已生成: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
