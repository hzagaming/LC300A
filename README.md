# LC300A（落川OS 300型）

LC300A 是一个处于开发阶段的 x86_64 桌面 Linux 发行版。项目以 Debian Stable、Linux LTS、KDE Plasma、Wayland 和 Calamares 为基础，目标是生成可通过 UEFI 启动、可试用、可安装并可更新的桌面操作系统。

当前状态：**阶段 2 — 图形桌面（进行中）**。Plasma Wayland、SDDM、PipeWire、NetworkManager、基础桌面应用与品牌体验已接入 Live ISO，并通过 QEMU/OVMF 启动和真实帧缓冲 E2E；应用交互、实际网络与音频功能、安装器、原生 x86_64 发布验收及真实硬件兼容性仍待验证。

## 技术基线

- 目标架构：x86_64
- 固件：UEFI
- 基础系统：Debian 13（trixie）
- ISO 工具：debootstrap + Debian live-build
- 桌面：KDE Plasma / Wayland / XWayland
- 安装器：Calamares
- 系统服务：systemd、NetworkManager、PipeWire、BlueZ、AppArmor
- 应用分发：APT + Flatpak

产品名称、版本和颜色统一配置在 `branding/product.toml`。

原创“落川流光”品牌基础包含 light/dark 语义色、Logo、双主题壁纸、Plymouth 图形启动界面及可复现生成的启动/通知/警告声音。资产已接入启动流程、Plasma、SDDM 与 freedesktop 声音主题，默认关闭且禁止自动播放 BGM，详见 `docs/architecture/brand-experience.md`。

## 快速开始

```bash
make help
make doctor
make test
make lint
```

在 Debian 13/Ubuntu 24.04 x86_64 构建机上：

```bash
make bootstrap
make doctor-strict
make iso
make test-boot
make test-desktop
```

当前开发镜像为 2,684,534,784 字节、1,581 个包，SHA-256：`bd17e483d869a5875272c5f2a08df81c75be0129c511c4a223e3769dc1b9909b`。

### 启动系统

已有 ISO 时启动交互式虚拟机：

```bash
make run-uefi
```

GRUB 默认在 3 秒后进入带 LC300A 图形启动界面的 `落川OS 300型 Live`。如果画面停住或需要排错，在 GRUB 中按方向键选择 `Live (diagnostics)`，再按 Enter 查看完整启动日志。

只做自动验收时：

```bash
make test-boot
make test-desktop
```

`make doctor` 只诊断环境，不修改宿主机。`make bootstrap` 会明确请求确认后安装当前平台所需的开发依赖。

ISO 构建必须在 Debian/Ubuntu x86_64 环境完成。安装 Homebrew QEMU 后，macOS Apple Silicon 可运行已有 ISO 和执行 UEFI 模拟启动测试；发布验收仍以原生 x86_64 Linux 为准。详见 `docs/development/environment.md`。

## 项目文档

- `ROADMAP.md`：开发阶段与验收门槛
- `PROJECT_STATE.md`：当前真实进度和阻塞项
- `DECISIONS.md`：架构决策记录
- `SECURITY.md`：安全策略和威胁模型
- `docs/architecture/iso-build.md`：ISO 构建架构

## 许可证

项目自研代码以 `GPL-3.0-or-later` 授权。文档、品牌素材和第三方组件可能采用不同许可；发布前必须在 `LICENSES/` 中记录并满足对应条款。
