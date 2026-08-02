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


def validate_content_region(path: Path, minimum_dark_ratio: float) -> None:
    if not 0 < minimum_dark_ratio <= 1:
        raise ValueError("内容区域深色像素比例必须在 0 到 1 之间")
    width, height, pixels = ppm(path)
    left, right = int(width * 0.1), int(width * 0.9)
    top, bottom = int(height * 0.15), int(height * 0.85)
    dark = 0
    total = (right - left) * (bottom - top)
    for y in range(top, bottom):
        row = y * width * 3
        for x in range(left, right):
            offset = row + x * 3
            dark += sum(pixels[offset : offset + 3]) < 384
    ratio = dark / total
    if ratio < minimum_dark_ratio:
        raise ValueError(f"页面内容区域深色像素仅占 {ratio:.2%}")


def change_ratio(reference: Path, candidate: Path) -> float:
    width, height, reference_pixels = ppm(reference)
    candidate_width, candidate_height, candidate_pixels = ppm(candidate)
    if (candidate_width, candidate_height) != (width, height):
        raise ValueError("应用截图与桌面基准尺寸不一致")
    pixel_count = width * height
    step = max(1, pixel_count // 4096)
    changed = 0
    samples = 0
    for index in range(0, pixel_count, step):
        offset = index * 3
        reference_pixel = reference_pixels[offset : offset + 3]
        candidate_pixel = candidate_pixels[offset : offset + 3]
        changed += max(abs(left - right) for left, right in zip(reference_pixel, candidate_pixel)) >= 16
        samples += 1
    return changed / samples


def validate_transition(reference: Path, candidate: Path, minimum_change_ratio: float = 0.05) -> None:
    if not 0 < minimum_change_ratio <= 1:
        raise ValueError("截图变化比例必须在 0 到 1 之间")
    ratio = change_ratio(reference, candidate)
    if ratio < minimum_change_ratio:
        raise ValueError(f"应用启动后仅改变 {ratio:.1%} 的帧缓冲")


def validate_restoration(reference: Path, candidate: Path, maximum_change_ratio: float = 0.02) -> None:
    if not 0 <= maximum_change_ratio < 1:
        raise ValueError("桌面恢复变化比例必须在 0 到 1 之间")
    ratio = change_ratio(reference, candidate)
    if ratio > maximum_change_ratio:
        raise ValueError(f"应用关闭后仍有 {ratio:.1%} 的帧缓冲未恢复")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a QEMU desktop framebuffer")
    parser.add_argument("screenshot", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--minimum-change-ratio", type=float, default=0.05)
    parser.add_argument("--minimum-content-dark-ratio", type=float)
    parser.add_argument("--maximum-change-ratio", type=float)
    arguments = parser.parse_args()
    try:
        validate(arguments.screenshot)
        if arguments.minimum_content_dark_ratio is not None:
            validate_content_region(arguments.screenshot, arguments.minimum_content_dark_ratio)
        if arguments.reference:
            if arguments.maximum_change_ratio is None:
                validate_transition(arguments.reference, arguments.screenshot, arguments.minimum_change_ratio)
            else:
                validate_restoration(arguments.reference, arguments.screenshot, arguments.maximum_change_ratio)
    except (OSError, ValueError) as error:
        print(f"[ERROR] 桌面截图校验失败: {error}", file=sys.stderr)
        return 1
    if arguments.maximum_change_ratio is not None:
        print(f"[OK] 应用关闭后桌面已恢复: {arguments.screenshot}")
    elif arguments.reference:
        print(f"[OK] 应用窗口已显著改变真实帧缓冲: {arguments.screenshot}")
    else:
        print(f"[OK] 桌面截图包含有效且非纯色的图形内容: {arguments.screenshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
