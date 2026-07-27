#!/usr/bin/env python3

import hashlib
import json
import math
import re
import struct
import sys
import tomllib
import wave
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCT_PATH = PROJECT_ROOT / "branding/product.toml"
EXPERIENCE_PATH = PROJECT_ROOT / "branding/experience.toml"
SOUND_PATH = PROJECT_ROOT / "branding/sounds"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"


def load_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def relative_asset(value: str) -> Path:
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"资产路径不安全: {value}")
    path = (PROJECT_ROOT / relative).resolve()
    path.relative_to(PROJECT_ROOT)
    if not path.is_file():
        raise ValueError(f"资产不存在: {value}")
    return path


def luminance(color: str) -> float:
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise ValueError(f"颜色格式错误: {color}")
    channels = []
    for index in (1, 3, 5):
        value = int(color[index : index + 2], 16) / 255.0
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def validate_contrast(product: dict, experience: dict) -> None:
    minimum_text = experience["accessibility"]["minimum_text_contrast"]
    minimum_focus = experience["accessibility"]["minimum_focus_contrast"]
    for mode in ("light", "dark"):
        palette = product["colors"][mode]
        text_pairs = (
            ("text", "background"),
            ("text", "surface"),
            ("text_muted", "background"),
            ("text_muted", "surface"),
            ("on_primary", "primary"),
            ("danger", "surface"),
            ("success", "surface"),
        )
        for foreground, background in text_pairs:
            ratio = contrast_ratio(palette[foreground], palette[background])
            if ratio < minimum_text:
                raise ValueError(f"{mode}.{foreground}/{background} 对比度仅 {ratio:.2f}:1")
        for foreground in ("accent", "focus"):
            ratio = contrast_ratio(palette[foreground], palette["background"])
            if ratio < minimum_focus:
                raise ValueError(f"{mode}.{foreground}/background 对比度仅 {ratio:.2f}:1")


def validate_policy(experience: dict, sound_theme: dict) -> None:
    layout = experience["layout"]
    motion = experience["motion"]
    accessibility = experience["accessibility"]
    audio = experience["audio"]

    if layout["touch_target_px"] < 44 or layout["control_height_px"] < 32:
        raise ValueError("交互目标尺寸低于可用性基线")
    if not 0 < motion["fast_ms"] <= motion["standard_ms"] <= motion["slow_ms"] <= 300:
        raise ValueError("动效时长必须递增且不超过 300ms")
    if motion["reduced_motion_ms"] != 0 or not accessibility["respect_reduced_motion"]:
        raise ValueError("必须提供无动效模式")
    if not accessibility["respect_system_mute"]:
        raise ValueError("声音必须服从系统静音")
    for key in ("event_volume", "startup_volume", "background_music_volume"):
        if not 0.0 <= audio[key] <= 0.7:
            raise ValueError(f"audio.{key} 超出安全默认范围")
    if audio["background_music_enabled"] or audio["background_music_autoplay"]:
        raise ValueError("背景音乐必须默认关闭且禁止自动播放")
    if audio["quiet_hours_supported"]:
        raise ValueError("安静时段策略尚未实现，不得声明支持")

    ambient = sound_theme["sounds"]["ambient"]
    if ambient["enabled_by_default"] or ambient["autoplay"] or ambient["loop"]:
        raise ValueError("可选 BGM 预览不得默认启用、自动播放或循环")


def validate_svg(path: Path, expected_view_box: str) -> None:
    root = ET.parse(path).getroot()
    if root.tag != f"{{{SVG_NAMESPACE}}}svg" or root.attrib.get("viewBox") != expected_view_box:
        raise ValueError(f"SVG 尺寸或命名空间错误: {path.name}")
    title = root.find(f"{{{SVG_NAMESPACE}}}title")
    description = root.find(f"{{{SVG_NAMESPACE}}}desc")
    if title is None or not title.text or description is None or not description.text:
        raise ValueError(f"SVG 缺少无障碍标题或描述: {path.name}")
    forbidden = {f"{{{SVG_NAMESPACE}}}script", f"{{{SVG_NAMESPACE}}}foreignObject"}
    for element in root.iter():
        if element.tag in forbidden:
            raise ValueError(f"SVG 包含禁止元素: {path.name}")
        for value in element.attrib.values():
            if "http://" in value or "https://" in value or "javascript:" in value.lower():
                raise ValueError(f"SVG 包含外部引用: {path.name}")


def validate_audio(sound_theme: dict) -> None:
    manifest = json.loads((SOUND_PATH / "manifest.json").read_text(encoding="utf-8"))
    sample_rate = sound_theme["format"]["sample_rate"]
    peak_limit = sound_theme["format"]["peak_limit"]
    entries = {entry["id"]: entry for entry in manifest["files"]}
    if manifest.get("license") != sound_theme["theme"]["license"]:
        raise ValueError("声音清单许可证与主题配置不一致")
    if set(entries) != set(sound_theme["sounds"]):
        raise ValueError("声音清单与主题配置不一致")

    for sound_id, sound in sound_theme["sounds"].items():
        path = SOUND_PATH / sound["file"]
        content = path.read_bytes()
        entry = entries[sound_id]
        if hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError(f"声音哈希不匹配: {path.name}")
        with wave.open(str(path), "rb") as stream:
            if (
                stream.getnchannels() != 1
                or stream.getsampwidth() != 2
                or stream.getframerate() != sample_rate
                or stream.getcomptype() != "NONE"
            ):
                raise ValueError(f"声音格式错误: {path.name}")
            expected_frames = round(sound["duration_ms"] * sample_rate / 1000)
            if stream.getnframes() != expected_frames or entry["frames"] != expected_frames:
                raise ValueError(f"声音时长错误: {path.name}")
            frames = stream.readframes(stream.getnframes())
        samples = struct.unpack(f"<{len(frames) // 2}h", frames)
        peak = max(abs(sample) for sample in samples) / 32767.0
        edge_peak = max(abs(sample) for sample in (*samples[:32], *samples[-32:])) / 32767.0
        if not 0.03 < peak <= peak_limit + 1 / 32767:
            raise ValueError(f"声音峰值错误: {path.name}")
        if edge_peak > 0.01 or not math.isclose(peak, entry["peak"], abs_tol=0.0001):
            raise ValueError(f"声音边缘或清单峰值错误: {path.name}")


def validate() -> None:
    product = load_toml(PRODUCT_PATH)
    experience = load_toml(EXPERIENCE_PATH)
    sound_theme = load_toml(relative_asset(experience["assets"]["sound_theme"]))
    if sound_theme["theme"]["license"] != "CC-BY-SA-4.0":
        raise ValueError("原创品牌声音必须声明 CC-BY-SA-4.0")
    validate_contrast(product, experience)
    validate_policy(experience, sound_theme)
    validate_svg(relative_asset(experience["assets"]["logo"]), "0 0 256 256")
    validate_svg(relative_asset(experience["assets"]["wallpaper_light"]), "0 0 3840 2160")
    validate_svg(relative_asset(experience["assets"]["wallpaper_dark"]), "0 0 3840 2160")
    validate_audio(sound_theme)


def main() -> int:
    try:
        validate()
    except (KeyError, OSError, ValueError, wave.Error, ET.ParseError, json.JSONDecodeError) as error:
        print(f"[ERROR] 品牌体验校验失败: {error}", file=sys.stderr)
        return 1
    print("[OK] 品牌体验、对比度、SVG 与音频校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
