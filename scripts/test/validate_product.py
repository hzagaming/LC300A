#!/usr/bin/env python3

import re
import sys
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


def load_config(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"无法读取产品配置: {error}") from error


def require(config: dict, section: str, key: str, expected_type: type = str):
    value = config.get(section, {}).get(key)
    if type(value) is not expected_type or (expected_type is str and not value.strip()):
        raise ValueError(f"{section}.{key} 缺失或类型错误")
    return value


def validate_config(config: dict) -> dict:
    product_id = require(config, "product", "id")
    product_name = require(config, "product", "name")
    version = require(config, "product", "version")
    version_id = require(config, "product", "version_id")
    channel = require(config, "product", "channel")
    suite = require(config, "base", "suite")
    architecture = require(config, "base", "architecture")
    firmware = require(config, "base", "firmware")
    live_user = require(config, "identity", "live_user")
    iso_name = require(config, "artifacts", "iso_name")
    output_directory = require(config, "artifacts", "output_directory")
    minimum_storage = require(config, "requirements", "minimum_storage_gib", int)
    recommended_storage = require(
        config, "requirements", "recommended_storage_gib", int
    )
    minimum_memory = require(config, "requirements", "minimum_memory_gib", int)
    typical_install = require(config, "requirements", "typical_install_gib", int)

    require(config, "product", "display_name")
    require(config, "product", "variant")
    hostname_prefix = require(config, "identity", "hostname_prefix")
    require(config, "identity", "os_release_id")

    if not re.fullmatch(r"[a-z][a-z0-9-]{1,31}", product_id):
        raise ValueError("product.id 必须是安全的小写系统标识")
    semver_component = r"(?:0|[1-9]\d*)"
    if not re.fullmatch(rf"{semver_component}\.{semver_component}\.{semver_component}", version_id):
        raise ValueError("product.version_id 必须是语义化版本号")
    if version != version_id and not version.startswith(f"{version_id}-"):
        raise ValueError("product.version 必须与 version_id 对应")
    if channel not in {"development", "testing", "stable"}:
        raise ValueError("product.channel 不受支持")
    if (suite, architecture, firmware) != ("trixie", "amd64", "uefi"):
        raise ValueError("基础系统必须符合 ADR-001 和 ADR-004")
    if live_user == "root" or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", live_user):
        raise ValueError("identity.live_user 不是安全的普通用户名")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", hostname_prefix):
        raise ValueError("identity.hostname_prefix 不是有效的主机名前缀")
    if require(config, "identity", "os_release_id") != product_id:
        raise ValueError("identity.os_release_id 必须等于 product.id")

    expected_iso = f"{product_name}-x86_64.iso"
    if iso_name != expected_iso or PurePosixPath(iso_name).name != iso_name:
        raise ValueError(f"artifacts.iso_name 必须为 {expected_iso}")
    output_path = PurePosixPath(output_directory)
    if output_path.is_absolute() or ".." in output_path.parts or output_directory != "build/artifacts":
        raise ValueError("artifacts.output_directory 必须是 build/artifacts")
    if minimum_storage < 16:
        raise ValueError("requirements.minimum_storage_gib 不得低于 16 GiB")
    if recommended_storage < minimum_storage:
        raise ValueError("requirements.recommended_storage_gib 不得低于最低磁盘要求")
    if minimum_memory < 2:
        raise ValueError("requirements.minimum_memory_gib 不得低于 2 GiB")
    if typical_install <= 0 or typical_install > minimum_storage:
        raise ValueError("requirements.typical_install_gib 必须大于 0 且不超过最低磁盘要求")

    for key in ("home_url", "support_url"):
        parsed = urlsplit(require(config, "identity", key))
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError(f"identity.{key} 必须是无凭据的 HTTPS URL")
    color_sections = {
        "brand": ("primary", "accent", "background", "foreground"),
        "light": (
            "background", "surface", "surface_alt", "text", "text_muted", "primary",
            "on_primary", "accent", "focus", "danger", "success",
        ),
        "dark": (
            "background", "surface", "surface_alt", "text", "text_muted", "primary",
            "on_primary", "accent", "focus", "danger", "success",
        ),
    }
    colors = config.get("colors", {})
    for section, keys in color_sections.items():
        palette = colors.get(section, {})
        for key in keys:
            value = palette.get(key)
            if not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
                raise ValueError(f"colors.{section}.{key} 必须是六位十六进制颜色")

    return config


def validate(path: Path) -> dict:
    return validate_config(load_config(path))


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) == 2 else "branding/product.toml")
    try:
        config = validate(path)
    except ValueError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    print(
        f"[OK] 产品配置有效: {config['product']['name']} "
        f"{config['product']['version']} ({config['base']['suite']}/{config['base']['architecture']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
