# 更新日志

本项目遵循语义化版本。开发版本只有在对应阶段的真实验收通过后才记录为完成。

## [0.3.0-dev] - 2026-07-31

### Added

- 集成 Calamares 图形安装器、品牌欢迎页、ext4/GPT/UEFI 分区、用户创建和 GRUB 安装流程。
- 添加桌面安装入口、应用菜单收藏与完整离线安装 E2E。
- 添加安装后移除 ISO 再启动、串口登录、SDDM 登录及 Plasma 桌面验收。

### Changed

- SDDM 改用深色品牌壁纸和高对比度前景色。
- Calamares 按钮与输入控件扩大到至少 44 px 的交互高度。

### Fixed

- 修复安装器启动时 `systemd-inhibit` 触发 Polkit 超时的问题。
- 修复 Debian 13 清理不存在的 `live-task-*` 软件包导致离线安装失败的问题。
- 补齐安装所需的 `hwclock` 与离线 GRUB EFI 软件包。
- 修复安装器分区页无效指针注入、普通用户 PATH 导致的 `hwclock` 假失败和桌面测试资源竞争造成的假性超时。

## [0.2.0] - 2026-07-29

### Added

- 集成 Plasma Wayland、SDDM、PipeWire、NetworkManager 与基础桌面应用。
- 接入“落川流光”Logo、壁纸、配色、声音主题和 Plymouth 图形启动体验。
- 提供图形桌面与纯文字 GRUB 启动模式。
- 将 Firefox ESR、Discover、Dolphin 与 Konsole 加入系统级收藏。
- 添加桌面帧缓冲、应用联网和非静音音频 E2E。

## [0.1.0] - 2026-07-26

### Added

- 实现 live-build 组装、Debian 13 rootfs、Linux、systemd、Live 用户与串口启动标记。
- 生成 GRUB BIOS/UEFI hybrid ISO、内部/外部 SHA-256、包清单与构建清单。
- 添加 QEMU q35、OVMF 与真实 UEFI 启动验收。

### Fixed

- 修复非交互 APT、Debian archive keyring、固件发现、sysvinit 冲突与 QEMU 清理问题。

## 阶段 0 - 2026-07-26

### Added

- 建立项目结构、产品配置、文档、环境诊断、引导脚本与基础 CI。
- 添加产品配置、仓库卫生、凭据扫描、构建环境和清理契约。
- 建立原创 Logo、双主题壁纸、可复现 SFX/BGM 与无障碍验证。
