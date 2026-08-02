#!/usr/bin/env python3

import argparse
import struct
import sys
import wave
from pathlib import Path


def read_pcm(path: Path) -> tuple[int, int, int, bytes]:
    try:
        with wave.open(str(path), "rb") as stream:
            return (
                stream.getsampwidth(),
                stream.getframerate(),
                stream.getnchannels(),
                stream.readframes(stream.getnframes()),
            )
    except wave.Error:
        content = path.read_bytes()
        if len(content) < 44 or content[:4] != b"RIFF" or content[8:12] != b"WAVE":
            raise
        if struct.unpack_from("<I", content, 4)[0] != 0:
            raise
        format_size = struct.unpack_from("<I", content, 16)[0]
        if content[12:16] != b"fmt " or format_size < 16:
            raise ValueError("QEMU 音频输出缺少 PCM 格式块")
        audio_format, channels, frame_rate, _, _, bits = struct.unpack_from("<HHIIHH", content, 20)
        data_offset = 20 + format_size
        if content[data_offset : data_offset + 4] != b"data":
            raise ValueError("QEMU 音频输出缺少数据块")
        data_size = struct.unpack_from("<I", content, data_offset + 4)[0]
        if audio_format != 1 or data_size != 0:
            raise ValueError("QEMU 流式音频头格式无效")
        return bits // 8, frame_rate, channels, content[data_offset + 8 :]


def validate(path: Path, minimum_duration: float = 0.5, minimum_peak: int = 256) -> tuple[float, int, int]:
    if minimum_duration <= 0 or not 0 < minimum_peak <= 32767:
        raise ValueError("音频校验阈值无效")
    sample_width, frame_rate, channels, frames = read_pcm(path)
    if sample_width != 2 or frame_rate <= 0 or channels <= 0:
        raise ValueError("仅支持有效的 16-bit PCM WAV")
    frame_size = sample_width * channels
    if not frames or len(frames) % frame_size:
        raise ValueError("PCM 音频包含不完整帧")
    frame_count = len(frames) // frame_size
    duration = frame_count / frame_rate
    if duration < minimum_duration:
        raise ValueError(f"音频输出仅持续 {duration:.2f} 秒")
    samples = [int.from_bytes(frames[index : index + 2], "little", signed=True) for index in range(0, len(frames), 2)]
    peak = max((abs(sample) for sample in samples), default=0)
    nonzero = sum(sample != 0 for sample in samples)
    if peak < minimum_peak or nonzero == 0:
        raise ValueError(f"音频输出为静音（峰值 {peak}，非零采样 {nonzero}）")
    return duration, peak, nonzero


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate audible PCM captured by QEMU")
    parser.add_argument("wav", type=Path)
    parser.add_argument("--minimum-duration", type=float, default=0.5)
    parser.add_argument("--minimum-peak", type=int, default=256)
    arguments = parser.parse_args()
    try:
        duration, peak, nonzero = validate(
            arguments.wav, arguments.minimum_duration, arguments.minimum_peak
        )
    except (EOFError, OSError, ValueError, wave.Error) as error:
        print(f"[ERROR] 音频输出校验失败: {error}", file=sys.stderr)
        return 1
    print(f"[OK] QEMU 音频输出有效：{duration:.2f} 秒，峰值 {peak}，非零采样 {nonzero}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
