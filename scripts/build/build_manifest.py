#!/usr/bin/env python3

import argparse
import datetime
import hashlib
import json
import platform
import subprocess
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def command(*arguments: str) -> str:
    return subprocess.run(
        arguments,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_manifest(iso: Path, packages: Path) -> dict:
    product = tomllib.loads(
        (PROJECT_ROOT / "branding/product.toml").read_text(encoding="utf-8")
    )
    commit = command("git", "rev-parse", "HEAD")
    dirty = bool(command("git", "status", "--porcelain"))
    manifest = {
        "schema_version": 1,
        "product": product["product"]["name"],
        "display_name": product["product"]["display_name"],
        "version": product["product"]["version"],
        "channel": product["product"]["channel"],
        "base": product["base"],
        "git_commit": commit,
        "git_dirty": dirty,
        "source_date_epoch": int(command("git", "show", "-s", "--format=%ct", commit)),
        "build_time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "build_host": {
            "system": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
        },
        "live_build_version": command("lb", "--version"),
        "iso": {
            "file": iso.name,
            "bytes": iso.stat().st_size,
            "sha256": sha256(iso),
        },
        "package_manifest": packages.name,
        "package_count": sum(1 for line in packages.read_text().splitlines() if line),
    }
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the LC300A ISO build manifest")
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--packages", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    manifest = create_manifest(arguments.iso, arguments.packages)
    arguments.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] 构建清单已生成: {arguments.output}")


if __name__ == "__main__":
    main()
