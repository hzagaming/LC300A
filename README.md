# LC300A（落川OS 300型）

LC300A 是一个处于开发阶段的 x86_64 桌面 Linux 发行版。项目以 Debian Stable、Linux LTS、KDE Plasma、Wayland 和 Calamares 为基础，目标是生成可通过 UEFI 启动、可试用、可安装并可更新的桌面操作系统。

当前状态：**阶段 0 — 项目初始化**。仓库尚未生成可启动 ISO，也未声明任何真实硬件兼容性。

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

原创“落川流光”品牌基础包含 light/dark 语义色、Logo、双主题壁纸及可复现生成的启动/通知/警告声音。资产目前尚未安装到桌面环境，详见 `docs/architecture/brand-experience.md`。

## 快速开始

```bash
make help
make doctor
make test
make lint
```

`make doctor` 只诊断环境，不修改宿主机。`make bootstrap` 会明确请求确认后安装当前平台所需的开发依赖。

ISO 的最终构建和启动测试必须在 Debian/Ubuntu x86_64 环境完成。macOS Apple Silicon 仅支持项目开发、静态检查，以及通过虚拟机或远程 x86_64 Linux 构建机进行构建。详见 `docs/development/environment.md`。

## 项目文档

- `ROADMAP.md`：开发阶段与验收门槛
- `PROJECT_STATE.md`：当前真实进度和阻塞项
- `DECISIONS.md`：架构决策记录
- `SECURITY.md`：安全策略和威胁模型
- `docs/architecture/iso-build.md`：ISO 构建架构

## 许可证

项目自研代码以 `GPL-3.0-or-later` 授权。文档、品牌素材和第三方组件可能采用不同许可；发布前必须在 `LICENSES/` 中记录并满足对应条款。
