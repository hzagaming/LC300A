# 项目状态

最后更新：2026-07-29

## 当前阶段

阶段 2：图形桌面（完成）；下一阶段为阶段 3 图形安装器。

## 当前事实

- 仓库已建立阶段 0 工程基线。
- 产品配置为 LC300A / 落川OS 300型，开发版本 `0.0.1-dev`。
- 产品配置具有版本、系统标识、基础套件、URL、颜色和产物路径校验。
- 仓库统一使用 LF 行尾，并拒绝常见凭据、环境文件、运行时缓存和大型系统产物进入源码树。
- bootstrap 和 doctor 只接受 Debian 13（trixie）或 Ubuntu 24.04 x86_64 构建环境。
- 已建立“落川流光”品牌基础：语义色、Logo、双主题壁纸、启动/通知/警告音及默认关闭的可选 BGM 预览。
- 已实现 live-build rootfs、显式 Debian 安全源、GRUB BIOS/UEFI hybrid ISO、Live 用户、root 锁定、串口启动标记、哈希/包清单/构建清单和 QEMU/OVMF 测试。
- 当前宿主机为 macOS 26.4 arm64；通过 QEMU/Lima 模拟的 Ubuntu 24.04 x86_64 构建机生成 ISO，宿主 QEMU 11.0.3 完成 UEFI 启动测试。
- Plasma、Wayland、XWayland、SDDM、PipeWire、NetworkManager、Firefox、Dolphin、Konsole 与“落川流光”品牌资产已接入 Live ISO。
- GRUB 提供图形桌面与纯文字两种明确模式；图形模式接入 Plymouth、SDDM/Live 自动登录和 Plasma，文字模式直接进入 multi-user 控制台。
- Firefox ESR、Discover、Dolphin 与 Konsole 已加入系统级应用菜单收藏；Discover 默认限制为已验证稳定的 PackageKit 与 Flatpak 后端，规避上游多后端异步崩溃。
- 阶段 2 镜像已通过自动登录、Plasma/Wayland、D-Bus、真实帧缓冲、应用交互、外网访问和非静音音频 E2E；安装器及真实硬件支持尚未验证。

## 已验证

在 macOS 26.4 arm64 宿主机实际执行：

- `make help`：通过，列出全部统一命令。
- `make doctor`：通过诊断；验证 Python 3.11+/tomllib，正确报告 macOS 不是 ISO 构建环境，并检测 Homebrew QEMU 与 ShellCheck。
- `make lint STRICT=1`：21 个 Shell/系统脚本、产品配置、品牌体验、live-build/桌面契约、仓库卫生和 ShellCheck 全部通过。
- `make test`：40 个单元测试、4 个 os-release fixture、bootstrap 与构建清理契约通过；项目文件、目录、产物隔离、Git 忽略规则、LF 行尾、命令入口和未开放阶段门禁通过。
- 品牌体验检查：light/dark 文本与焦点对比度、SVG 安全和无障碍元数据、4 个 WAV 的格式/峰值/边缘/哈希及确定性重生成通过。
- 视觉 QA：使用 macOS 本地 SVG 渲染器检查 Logo、32/48 px 图标与两张 3840×2160 壁纸，通过。
- `./scripts/bootstrap/macos.sh --check`：通过，识别 Apple Silicon 并输出 x86_64 Linux 构建方案。
- `make doctor-strict`：按预期失败，拒绝将当前宿主机视为完整构建环境。
- `git diff --check`：通过。
- CI YAML 本地语法解析通过；GitHub Actions 因本机缺少 GitHub 凭据尚未实际运行。
- Ubuntu 24.04 x86_64：bootstrap、严格 doctor、lint、test 与 `make iso` 通过，生成 ISO 及 SHA-256、包清单、构建清单和日志。
- xorriso 验证 ISO 含 protective MBR、GPT、BIOS GRUB 和 EFI El Torito 启动项；宿主 QEMU/OVMF `make test-boot` 检测到 `LC300A_BOOT_OK`。
- 当前阶段 2 ISO 为 1,788,637,184 字节、1,581 个包，SHA-256 为 `b1e3aac4dcd74fdcec00e25d74260fa273551f9b756f68519c59e6585fd01501`。
- 启动标记出现前已验证 Live 用户、home、有效 shell 和 sudo 组，不再错误绑定固定 tty。
- `make test-console` 自动选择第二个 GRUB 项并检测到 `LC300A_CONSOLE_OK`，确认未启动图形目标且完整 systemd 日志可见。
- `make test-boot` 在 quiet/splash 默认路径检测到 `LC300A_BOOT_OK`；18–30 秒启动帧显示 Logo、渐变背景、标题和 `STARTING` 呼吸指示器，连续八帧哈希均不同。
- `make test-desktop` 检测到 `LC300A_DESKTOP_OK`，并验证 1280×800 真实帧缓冲已绘制品牌壁纸、Plasma 面板与系统托盘，且不再自动弹出上游 Welcome Center；就绪探针失败关闭，截图校验拒绝纯色及大面积黑屏。
- `make test-apps` 通过双向串口登录 Plasma 用户会话，验证 Konsole、Firefox 和 Discover 保持 active 且绘制真实窗口；Firefox 成功打开 `https://example.com`，Discover 默认启动未再崩溃。
- 同一应用 E2E 通过 QEMU HDA/WAV 后端捕获 9.29 秒 44.1kHz/16-bit/stereo PCM，峰值 7843、非零采样 297,264，确认 PipeWire 实际输出非静音音频。

## 已知阻塞与限制

- Debian 13 原生构建机和 GitHub Actions 尚未验证；当前真实构建环境是 Ubuntu 24.04 x86_64 模拟机。
- macOS 上的 x86_64 TCG 只用于开发验收，不能替代原生 x86_64 发布性能与硬件测试。
- 麦克风输入、蓝牙音频和真实声卡仍未验证；当前音频验收只覆盖 QEMU HDA 输出。
- 远端推送因本机 GitHub HTTPS/SSH 凭据缺失而失败，CI 尚未触发。
- LC300A 自有软件源签名密钥和发布基础设施尚未创建；这些不阻塞阶段 2 开发。
- GPL-3.0-or-later 与 CC BY-SA 4.0 的完整许可证正文尚未从可信来源引入。

## 下一优先任务

开始阶段 3 Calamares 图形安装器、虚拟硬盘安装与重启登录 E2E。
