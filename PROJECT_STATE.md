# 项目状态

最后更新：2026-07-26

## 当前阶段

阶段 2：图形桌面（待开始；阶段 1 最小可启动 ISO 已完成验收）。

## 当前事实

- 仓库已建立阶段 0 工程基线。
- 产品配置为 LC300A / 落川OS 300型，开发版本 `0.0.1-dev`。
- 产品配置具有版本、系统标识、基础套件、URL、颜色和产物路径校验。
- 仓库统一使用 LF 行尾，并拒绝常见凭据、环境文件、运行时缓存和大型系统产物进入源码树。
- bootstrap 和 doctor 只接受 Debian 13（trixie）或 Ubuntu 24.04 x86_64 构建环境。
- 已建立“落川流光”品牌基础：语义色、Logo、双主题壁纸、启动/通知/警告音及默认关闭的可选 BGM 预览。
- 已实现 live-build rootfs、显式 Debian 安全源、GRUB BIOS/UEFI hybrid ISO、Live 用户、root 锁定、串口启动标记、哈希/包清单/构建清单和 QEMU/OVMF 测试。
- 当前宿主机为 macOS 26.4 arm64；通过 QEMU/Lima 模拟的 Ubuntu 24.04 x86_64 构建机生成 ISO，宿主 QEMU 11.0.3 完成 UEFI 启动测试。
- 品牌资产尚未安装到 Plasma/SDDM，阶段 1 产物是可用控制台 Live 系统，不是图形桌面成品。
- 未验证安装器、桌面或真实硬件支持。

## 已验证

在 macOS 26.4 arm64 宿主机实际执行：

- `make help`：通过，列出全部统一命令。
- `make doctor`：通过诊断；验证 Python 3.11+/tomllib，正确报告 macOS 不是 ISO 构建环境，并检测 Homebrew QEMU 与 ShellCheck。
- `make lint STRICT=1`：17 个 Shell/系统脚本、产品配置、品牌体验、live-build 契约、仓库卫生和 ShellCheck 全部通过。
- `make test`：25 个单元测试、4 个 os-release fixture、bootstrap 与构建清理契约通过；项目文件、目录、产物隔离、Git 忽略规则、LF 行尾、命令入口和未开放阶段门禁通过。
- 品牌体验检查：light/dark 文本与焦点对比度、SVG 安全和无障碍元数据、4 个 WAV 的格式/峰值/边缘/哈希及确定性重生成通过。
- 视觉 QA：使用 macOS 本地 SVG 渲染器检查 Logo 与两张 3840×2160 壁纸，通过。
- `./scripts/bootstrap/macos.sh --check`：通过，识别 Apple Silicon 并输出 x86_64 Linux 构建方案。
- `make doctor-strict`：按预期失败，拒绝将当前宿主机视为完整构建环境。
- `git diff --check`：通过。
- CI YAML 本地语法解析通过；GitHub Actions 因本机缺少 GitHub 凭据尚未实际运行。
- Ubuntu 24.04 x86_64：bootstrap、严格 doctor、lint、test 与 `make iso` 通过，生成约 381 MiB ISO 及 SHA-256、包清单、构建清单和日志。
- xorriso 验证 ISO 含 protective MBR、GPT、BIOS GRUB 和 EFI El Torito 启动项；宿主 QEMU/OVMF `make test-boot` 检测到 `LC300A_BOOT_OK`。
- 启动标记出现前已验证 Live 用户、home、有效 shell、sudo 组和 `getty@tty1`。

## 已知阻塞与限制

- Debian 13 原生构建机和 GitHub Actions 尚未验证；当前真实构建环境是 Ubuntu 24.04 x86_64 模拟机。
- macOS 上的 x86_64 TCG 只用于开发验收，不能替代原生 x86_64 发布性能与硬件测试。
- 远端推送因本机 GitHub HTTPS/SSH 凭据缺失而失败，CI 尚未触发。
- LC300A 自有软件源签名密钥和发布基础设施尚未创建；这些不阻塞阶段 2 开发。
- GPL-3.0-or-later 与 CC BY-SA 4.0 的完整许可证正文尚未从可信来源引入。

## 下一优先任务

开始阶段 2：加入 KDE Plasma、Wayland、SDDM、PipeWire 与品牌桌面集成，并建立自动登录和桌面 E2E 验收。
