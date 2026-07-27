#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


def ppm(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    parts = data.split(b"\n", 3)
    if len(parts) != 4 or parts[0] != b"P6" or parts[2] != b"255":
        raise ValueError("截图不是 QEMU P6 PPM 格式")
    try:
        width, height = (int(value) for value in parts[1].split())
    except (TypeError, ValueError) as error:
        raise ValueError("截图尺寸头无效") from error
    pixels = parts[3]
    if width <= 0 or height <= 0 or len(pixels) != width * height * 3:
        raise ValueError("截图像素数据长度错误")
    return width, height, pixels


def validate(path: Path, minimum_width: int = 800, minimum_height: int = 600) -> None:
    width, height, pixels = ppm(path)
    if width < minimum_width or height < minimum_height:
        raise ValueError(f"桌面分辨率过低: {width}x{height}")
    pixel_count = width * height
    step = max(1, pixel_count // 4096)
    samples = [pixels[index * 3 : index * 3 + 3] for index in range(0, pixel_count, step)]
    colors = set(samples)
    luminance = [sum(pixel) / 3 for pixel in samples]
    if len(colors) < 24 or max(luminance) - min(luminance) < 24:
        raise ValueError("桌面截图为黑屏、纯色或尚未完成绘制")
    if sum(max(pixel) < 16 for pixel in samples) / len(samples) > 0.5:
        raise ValueError("桌面背景仍为黑屏或尚未完成绘制")
    if sum(luminance) / len(luminance) < 5:
        raise ValueError("桌面截图平均亮度过低")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a QEMU desktop framebuffer")
    parser.add_argument("screenshot", type=Path)
    arguments = parser.parse_args()
    try:
        validate(arguments.screenshot)
    except (OSError, ValueError) as error:
        print(f"[ERROR] 桌面截图校验失败: {error}", file=sys.stderr)
        return 1
    print(f"[OK] 桌面截图包含有效且非纯色的图形内容: {arguments.screenshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
