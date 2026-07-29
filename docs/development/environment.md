# 开发环境

## 支持矩阵

| 环境 | 编辑/静态检查 | ISO 构建 | 已有 ISO 启动 | 发布验收 |
| --- | :---: | :---: | :---: | :---: |
| Debian 13 x86_64 | 是 | 是 | 是 | 是 |
| Ubuntu 24.04 x86_64 | 是 | 是 | 是 | 是 |
| macOS Apple Silicon | 是 | 否 | QEMU 模拟 | 否 |

先运行 `make doctor`。该命令只报告环境，不安装软件。`make doctor-strict` 仅在完整的 x86_64 Linux 工具链上成功。

构建脚本会拒绝 Debian 12、Ubuntu 22.04 和其他未列入支持矩阵的版本，避免因软件包版本漂移产生不可复现结果。

## Debian/Ubuntu

```bash
make bootstrap
make doctor-strict
make lint
make test
make iso
make test-boot
make test-console
make test-desktop
make test-apps
```

`make bootstrap` 会在安装依赖前请求确认。CI 中如需非交互安装，必须显式设置 `LC300A_ASSUME_YES=1`。ISO、校验值、构建清单、包清单和串口日志写入 `build/artifacts/`。

`make test-apps` 使用 QEMU 双向串口驱动 Plasma 用户会话，并生成应用帧缓冲截图与音频捕获；测试期间需要访问 `https://example.com`。

## macOS Apple Silicon

```bash
make doctor
./scripts/bootstrap/macos.sh --check
```

如需安装宿主侧 QEMU 和 ShellCheck，可执行 `make bootstrap` 并确认 Homebrew 操作。随后准备 Debian/Ubuntu x86_64 虚拟机或远程构建机，在 Linux 环境重新运行严格检查。Apple Silicon 上对 x86_64 的 QEMU 属于模拟，性能较低。

已有 `build/artifacts/LC300A-x86_64.iso` 时：

```bash
make run-uefi
# 或执行无界面串口验收
BOOT_TIMEOUT_SECONDS=600 make test-boot
```

验证候选镜像且不覆盖默认产物时，可传入绝对或相对路径：

```bash
LC300A_ISO_PATH=/tmp/LC300A-candidate.iso make test-boot
LC300A_ISO_PATH=/tmp/LC300A-candidate.iso make test-desktop
```
