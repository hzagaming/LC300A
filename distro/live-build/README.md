# live-build 输入

该目录保存阶段 1 的构建契约说明；实际 `config/` 由 `scripts/build/configure_live.py` 在 `build/live-build/work/` 中生成。

版本控制输入来自：

- `distro/package-lists/`
- `distro/overlays/`
- `distro/hooks/`
- `branding/product.toml`

不得手工修改 `build/live-build/work/config/`，因为下次配置会重新生成。
