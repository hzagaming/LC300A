#!/usr/bin/env python3

import os
import re
import sys
from pathlib import Path


SKIP_DIRECTORIES = {".git", "build"}
RUNTIME_DIRECTORIES = {
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "venv",
}
SENSITIVE_SUFFIXES = {".iso", ".key", ".p12", ".pfx", ".pyc", ".qcow2", ".raw"}
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:EC |OPENSSH |RSA )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bghp_[A-Za-z0-9]{36,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
)


def inspect_repository(root: Path) -> tuple[list[str], int]:
    errors = []
    checked = 0

    for current, directories, files in os.walk(root):
        current_path = Path(current)
        kept_directories = []
        for name in directories:
            if name in SKIP_DIRECTORIES:
                continue
            if name in RUNTIME_DIRECTORIES:
                errors.append(f"禁止提交运行时目录: {(current_path / name).relative_to(root)}")
                continue
            kept_directories.append(name)
        directories[:] = kept_directories

        for name in files:
            path = current_path / name
            relative = path.relative_to(root)
            checked += 1

            if name == ".DS_Store" or (name.startswith(".env") and name != ".env.example"):
                errors.append(f"禁止提交宿主机或环境文件: {relative}")
                continue
            if path.suffix.lower() in SENSITIVE_SUFFIXES:
                errors.append(f"禁止提交敏感或生成文件: {relative}")
                continue
            if path.is_symlink() or path.stat().st_size > 1024 * 1024:
                continue

            content = path.read_bytes()
            if b"\0" in content:
                continue
            if any(pattern.search(content) for pattern in SECRET_PATTERNS):
                errors.append(f"检测到高置信度凭据内容: {relative}")

    return errors, checked


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) == 2 else ".").resolve()
    errors, checked = inspect_repository(root)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    print(f"[OK] 仓库卫生检查通过（检查 {checked} 个文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
