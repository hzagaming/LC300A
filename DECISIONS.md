# 架构决策

## ADR-001：基于 Debian Stable 构建

- 状态：接受
- 日期：2026-07-25

选择 Debian 13（trixie）、debootstrap 和 live-build，复用成熟内核、驱动、软件包与安全更新体系。项目不从零实现内核、图形栈、网络栈或包管理器。

## ADR-002：首版桌面采用 KDE Plasma Wayland

- 状态：接受
- 日期：2026-07-25

首版使用 KDE Plasma、Wayland、XWayland 和 SDDM，以系统级默认配置实现品牌体验。图形界面不直接以 root 权限运行。

## ADR-003：产品配置集中管理

- 状态：接受
- 日期：2026-07-25

名称、版本、标识、颜色、网站与仓库地址统一定义在 `branding/product.toml`。生成系统文件时从该配置派生，避免品牌值散落硬编码。

## ADR-004：ISO 仅在 x86_64 Linux 环境构建和验收

- 状态：接受
- 日期：2026-07-25

最终 ISO 构建与 QEMU/OVMF 启动测试在 Debian/Ubuntu x86_64 环境执行。macOS Apple Silicon 只作为开发宿主机，通过虚拟机、容器或远程构建机提供 Linux 环境，不伪装成本地完整构建。

## ADR-005：第一版安装文件系统使用 ext4

- 状态：接受
- 日期：2026-07-25

第一版安装器使用 ext4，降低安装与恢复复杂度。Btrfs 快照与原子回滚作为后续设计，不在早期阶段加入兼容层。

## ADR-006：品牌体验采用语义设计令牌和安静默认值

- 状态：接受
- 日期：2026-07-26

light/dark 颜色集中在 `branding/product.toml`，排版、布局、动效、可访问性和声音策略集中在 `branding/experience.toml`。背景音乐默认关闭且禁止自动播放；启动音服从系统静音，安静时段策略待实现。阶段 0 只提供经过验证的原创资产，不提前声明已集成桌面环境。

## ADR-007：无 3D Plasma 会话采用条件化软件渲染

- 状态：接受
- 日期：2026-07-27

virtio-pci DRM 在当前无 3D QEMU 路径中禁用 KWin atomic modesetting，其他 DRM 驱动保持默认；只有 KWin renderer 为 llvmpipe 时，PlasmaShell 才使用软件 Qt Quick。PlasmaShell 启动和桌面就绪状态都要求内核 DRM connector 实际启用，桌面就绪还要求 PlasmaShell D-Bus 可响应，并由 QEMU 真实帧缓冲验证；禁止仅凭进程或 KWin 逻辑输出存在报告成功。
