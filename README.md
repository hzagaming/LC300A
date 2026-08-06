# LC300A（落川OS 300型）

LC300A 是一个处于开发阶段的 x86_64 桌面 Linux 发行版。项目以 Debian Stable、Linux LTS、KDE Plasma、Wayland 和 Calamares 为基础，目标是生成可通过 UEFI 启动、可试用、可安装并可更新的桌面操作系统。

当前状态：**阶段 4 — 桌面体验和系统应用（进行中）**，首次登录欢迎体验与容量透明度增量已完成。Plasma Wayland、SDDM、PipeWire、NetworkManager、基础桌面应用、品牌体验、Calamares 与 Qt 6/QML 欢迎程序已接入 ISO，并通过 QEMU/OVMF 启动、真实帧缓冲、应用联网、非静音音频、完全断网安装、首次登录及安装后硬盘启动 E2E；原生 x86_64 发布验收及真实硬件兼容性仍待验证。

## 技术基线

- 目标架构：x86_64
- 固件：UEFI
- 基础系统：Debian 13（trixie）
- ISO 工具：debootstrap + Debian live-build
- 桌面：KDE Plasma / Wayland / XWayland
- 安装器：Calamares
- 系统服务：systemd、NetworkManager、PipeWire、BlueZ、AppArmor
- 应用分发：APT + Flatpak

产品名称、版本、容量要求和颜色统一配置在 `branding/product.toml`。

原创“落川流光”品牌基础包含 light/dark 语义色、Logo、双主题壁纸、Plymouth 图形启动界面及可复现生成的启动/通知/警告声音。资产已接入启动流程、Plasma、SDDM 与 freedesktop 声音主题，默认关闭且禁止自动播放 BGM，详见 `docs/architecture/brand-experience.md`。

## 容量与安装要求

- 最低磁盘：16 GiB
- 推荐磁盘：32 GiB
- 最低内存：2 GiB
- 典型安装：约 6 GiB

`0.3.6-dev` 全新构建的展开 rootfs 实测为 4,965,994,496 字节（约 4.63 GiB）。典型安装口径保留了日志、包管理缓存和基础更新空间；最低磁盘不是 ISO 文件大小。

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
make test-console
make test-desktop
make test-apps
make test-installer
```

当前 `0.3.6-dev` 开发镜像为 1,808,596,992 字节、1,618 个包，SHA-256：`88513683b522bae7d2e13f32fd7c8e30502cd79137c47c99b540f45756b06054`。

### 启动系统

已有 ISO 时启动交互式虚拟机：

```bash
make run-uefi
```

GRUB 默认在 3 秒后进入 `Live (图形桌面)`，显示 LC300A 启动画面并自动进入 Plasma。需要完整日志、低资源运行或排错时，选择 `Live (纯文字模式)`，该模式只启动 multi-user 文本控制台，不启动 SDDM 和 Plasma。

纯文字模式使用 Live 账户 `lc300a-live`，密码为 `live`；图形模式由 SDDM 自动登录，注销后会回到图形登录页。

图形桌面的应用菜单默认收藏欢迎程序、Firefox ESR、Discover 应用商店、Dolphin 文件管理器和 Konsole 终端。安装后首次登录会自动显示四步欢迎程序，Live 环境不弹出；完成后不会重复显示，也可随时从应用菜单重新打开。Discover 默认只启用 Debian PackageKit；配置系统级或用户级 Flatpak remote 后会自动追加 Flatpak 后端。

进入图形桌面后，可双击桌面上的“安装落川OS 300型”启动 Calamares。完整图形安装步骤与清盘风险说明见 `docs/installation/graphical-install.md`。

只做自动验收时：

```bash
make test-boot
make test-console
make test-desktop
make test-apps
make test-installer
```

`make doctor` 只诊断环境，不修改宿主机。`make bootstrap` 会明确请求确认后安装当前平台所需的开发依赖。

`make test-apps` 会实际登录 Live 串口会话，在 Plasma 用户会话中打开 Konsole、Dolphin、系统设置、欢迎程序四页、Firefox 和 Discover，验证真实窗口、URI 动作、Firefox 单标签 HTTPS/DNS/证书与正文、Discover 应用卡片，以及 QEMU 捕获的自动/手工非静音 PCM；该测试需要可访问 `https://example.com`。

ISO 构建必须在 Debian/Ubuntu x86_64 环境完成。安装 Homebrew QEMU 后，macOS Apple Silicon 可运行已有 ISO 和执行 UEFI 模拟启动测试；发布验收仍以原生 x86_64 Linux 为准。详见 `docs/development/environment.md`。

## 项目文档

- `ANNOUNCEMENT.md`：当前开发版本公告与镜像校验值
- `ROADMAP.md`：开发阶段与验收门槛
- `PROJECT_STATE.md`：当前真实进度和阻塞项
- `DECISIONS.md`：架构决策记录
- `SECURITY.md`：安全策略和威胁模型
- `docs/architecture/iso-build.md`：ISO 构建架构

## 许可证

项目自研代码以 `GPL-3.0-or-later` 授权。文档、品牌素材和第三方组件可能采用不同许可；发布前必须在 `LICENSES/` 中记录并满足对应条款。
