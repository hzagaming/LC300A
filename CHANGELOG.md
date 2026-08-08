# 更新日志

本项目遵循语义化版本。开发版本只有在对应阶段的真实验收通过后才记录为完成。

## [0.3.7-dev] - 2026-08-07

### Added

- 加入 Ark、Gwenview、Kate、KCalc 与 Kamoso，补齐归档、图片查看、文本编辑、计算器和相机入口。
- 显式提供 curl、wget、git、jq、htop、ripgrep、rsync、tree、zip/unzip 与 lsof 终端工具。
- 加入 zram 交换设备，并为新增 GUI 应用、CLI 工具、zram 与 Baloo 状态增加真实系统 E2E。

### Changed

- QEMU 默认资源从 4 GiB/4 vCPU 调整为 2 GiB/6 vCPU，TCG 启用多线程和 256 MiB 翻译块缓存，显示设备改为显式 1280×800 virtio-vga。
- 默认关闭 Baloo 文件索引，减少低配置环境的后台 CPU、内存和磁盘活动。
- 应用菜单收藏加入 Kate、KCalc 与 Kamoso，欢迎程序和登录欢迎语同步展示新增工具。

### Fixed

- 修复多线程 TCG 子参数错误混入 q35 机器属性、导致 QEMU 11 拒绝启动的问题。
- QEMU 内存与 vCPU 环境变量增加范围校验，拒绝无效或异常资源值。
- 修复 Kate E2E 使用非标准新窗口参数后进程提前退出的问题，并补充应用失败日志诊断。
- 首次登录欢迎程序改为等待 KSplash 退出后再启动；安装后 E2E 现在会识别真实欢迎窗口，避免把纯桌面误判为通过。

## [0.3.6-dev] - 2026-08-06

### Added

- 在产品配置中加入最低磁盘 16 GiB、推荐磁盘 32 GiB、最低内存 2 GiB 和典型安装约 6 GiB 的统一容量口径。
- 欢迎程序首页加入容量卡片，Calamares 欢迎模块从同一配置生成磁盘与内存门槛。
- 产品、桌面、安装器和 QML 渲染测试加入容量边界、类型、布局、分类和品牌版本层级回归断言。

### Changed

- 欢迎程序最小窗口调整为 800×600，常用入口固定为双列布局，并缩减首页留白避免低分辨率裁切。
- 当前开发版本、安装器品牌与生成内容统一更新至 `0.3.6-dev`。

### Fixed

- 修复离开声音页后试听仍可能继续，以及手工停止试听后反馈状态不准确的问题。
- 修复欢迎程序桌面入口同时注册两个主分类的问题。
- 修复安装器品牌 YAML 的版本字段脱离 `strings` 层级，并清除带版本产品名中的 `0.3.5` 残留。
- 修正文档中“Flatpak 后端默认启用”的错误描述；Discover 默认只使用 PackageKit，有 Flatpak remote 时才追加 Flatpak 后端。

## [0.3.5-dev] - 2026-08-05

### Added

- 加入 Qt 6/QML 四步首次登录欢迎程序，提供系统设置、Discover、隐私说明、支持入口和手工声音试听。
- 加入安装后首次显示、完成状态 `0600` 持久化、不重复弹窗及严格白名单 URI 动作处理。
- 应用 E2E 增加欢迎程序四页、Dolphin、系统设置、URI handler 和手工环境音验收。

### Changed

- 首次登录欢迎程序等待 PlasmaShell D-Bus 就绪并完成壁纸、面板绘制；手工启动不延迟。
- 安装器 E2E 在完成标记后等待 Finish 页连续稳定绘制，再启动安装后的系统。
- 应用菜单收藏加入欢迎程序，Live 环境继续禁止首次登录自动弹窗。

### Fixed

- 修复安装后欢迎窗口先于 Plasma 壁纸和面板绘制而出现黑底的问题。
- 修复 Calamares 97% 进度页可能被 E2E 误报为完成页的假阳性。

## [0.3.4-dev] - 2026-08-05

### Changed

- Discover 默认只启用 PackageKit，并在检测到系统级或用户级 Flatpak remote 后自动追加 Flatpak 后端。
- Firefox E2E 先独立验证 DNS、HTTPS、证书和正文，再直接启动单一目标页面窗口。
- Discover E2E 改为验证整个主内容区的彩色内容比例，并增加灰白错误页回归用例。

### Fixed

- 修复未配置 Flatpak remote 时 Discover 间歇显示 `Unable to load applications`，以及用户级 remote 未被发现的问题。
- 修复 Firefox E2E 启动浏览器后再次打开相同页面、产生重复标签的问题。
- 修复 Discover 错误页的小块彩色图标可能让固定坐标帧缓冲检查误判成功的问题。

## [0.3.3-dev] - 2026-08-03

### Changed

- Firefox ESR 关闭首次启动欢迎标签和默认数据提交，保留用户自主修改主页的能力。
- Calamares 宽度调整为 1080 px，完整显示开发版本欢迎标题。
- 安装器 E2E 改用无调试参数的生产启动路径，并在用户表单校验稳定后采集填写完成帧。
- 构建镜像源切换到可签名校验的清华 Debian 镜像，安装后 APT 使用对应 HTTPS 源。
- 构建末期显式下载 DEP-11 元数据并刷新 AppStream 系统缓存。

### Fixed

- 修复 Firefox 首次启动额外打开 Mozilla 欢迎/隐私标签的干扰。
- 修复 Debian 官方 CDN 不可达时 ISO 构建中断及 Discover 元数据刷新失败的问题。
- 修复手工音频播放失效时，旧启动音仍可能让最终音频校验通过的假阳性。
- 修复 Calamares 调试界面与用户实际启动外观不一致，以及加载旋转页可被颜色数量阈值误判为欢迎页的问题。
- 修复用户表单最后一个按键尚未渲染时，E2E 提前截取密码不一致错误态的问题。
- 修复 Discover 首次启动缺少软件目录和图标、显示 `Unable to load applications` 的问题。

## [0.3.2-dev] - 2026-08-02

### Changed

- Discover E2E 等待应用卡片和正文区域充分绘制，不再以窗口边框变化代表应用可用。
- 应用 E2E 在手工播放音频前验证自动会话启动音，并限制自动音频活跃时长以守住 BGM 默认关闭策略。
- 纯文字模式登录欢迎语改为从产品版本动态生成，并列出当前可用的桌面、浏览器、应用商店和图形安装器。

### Fixed

- 修复 Discover 长时间停留在 `Loading…` 时仍可能通过帧缓冲检查的假阳性。
- 修复手工播放启动音可能掩盖自动会话音效失效或 BGM 被意外自动播放的覆盖缺口。
- 修复纯文字模式仍显示过时阶段说明且缺少当前版本和主要图形功能的问题。

## [0.3.1-dev] - 2026-08-02

### Changed

- 扩大 Calamares 单选框和复选框的点击目标与状态图标，并增加清晰的键盘焦点边框。
- Firefox E2E 改为先验证真实 HTTPS、DNS、证书和页面内容，再驱动已运行的浏览器实例打开页面。
- Firefox 页面帧缓冲增加正文区域绘制门槛，空白标签页不再通过。
- 完整安装 E2E 增加 Calamares 完成页真实帧缓冲验收。

### Fixed

- 修复 QEMU 逐键输入丢失 `https:` 前缀却把 Firefox 错误页误判为联网成功的问题。
- 修复 QEMU 流式 WAV 末尾包含不完整 PCM 帧时仍可能通过音频校验的问题。

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
