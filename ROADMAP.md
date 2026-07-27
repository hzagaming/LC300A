# 路线图

阶段只有在对应测试实际通过后才能完成；不得以代码存在代替验收。

## 阶段 0：项目初始化（完成）

- [x] 建立仓库目录、产品配置和基础文档
- [x] 提供构建命令入口、宿主机诊断与引导脚本
- [x] 提供基础 CI 和阶段 0 测试
- [x] 建立可访问的品牌体验配置与原创视觉/声音资产

验收：`make help` 与 `make doctor` 可运行并准确报告缺失依赖。

## 阶段 1：最小可启动 ISO（0.1.0，完成）

实现 Debian rootfs、Linux 内核、systemd、GRUB UEFI、Live 用户、串口控制台、ISO 构建与 QEMU/OVMF 启动测试。

- [x] live-build 配置组装、核心包清单、overlay 和 chroot hook
- [x] rootfs/ISO 构建入口及 ISO 哈希、包清单、构建清单
- [x] QEMU q35、OVMF CODE/VARS 和串口启动标记测试
- [x] 在 Ubuntu 24.04 x86_64 构建 ISO 并通过 QEMU/OVMF UEFI `make test-boot`

验收：ISO 在 QEMU 中通过 UEFI 启动并进入 shell。

## 阶段 2：图形桌面（0.2.0，进行中）

实现 SDDM、KDE Plasma、Wayland、XWayland、基础品牌、网络、音频、文件管理器、终端和浏览器。

- [x] Plasma Wayland 与 SDDM Live 自动登录
- [x] NetworkManager、PipeWire、WirePlumber 与基础桌面应用
- [x] Logo、壁纸、配色、登录界面与声音主题
- [x] QEMU/OVMF 桌面就绪与真实帧缓冲 E2E
- [ ] 终端、浏览器、网络与音频功能 E2E

验收：Live ISO 自动进入桌面，终端和浏览器可用，网络与音频服务正常，并通过真实帧缓冲验收。

## 阶段 3：图形安装器（0.3.0）

集成 Calamares、ext4 分区、用户创建、GRUB 安装和虚拟硬盘安装测试。

验收：从 ISO 安装到 QEMU 虚拟硬盘后，可移除 ISO 并登录桌面。

## 阶段 4：桌面体验和系统应用（0.4.0）

实现欢迎程序、设置入口、更新程序、应用中心、系统报告、中英文界面和 Fcitx5。

## 阶段 5：仓库和更新基础设施（0.5.0）

实现签名 APT 仓库、Flatpak 集成、发布流程、版本管理和跨版本更新测试。

## 阶段 6：稳定性和兼容性（0.9.0）

验证 QEMU/KVM、VMware、VirtualBox、软件渲染、常见显卡、网络、蓝牙、音频、睡眠与失败恢复。

## 阶段 7：正式发布（1.0.0）

发布 ISO、校验值、包清单、SBOM、发布说明、已知问题、安装与恢复文档、安全和许可证清单。
