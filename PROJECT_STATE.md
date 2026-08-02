# 项目状态

最后更新：2026-08-02

## 当前阶段

阶段 3：图形安装器（完成）；下一阶段为阶段 4 桌面体验和系统应用。

## 当前事实

- 产品为 LC300A / 落川OS 300型，开发版本 `0.3.1-dev`，基于 Debian 13（trixie）amd64。
- ISO 提供 UEFI/GRUB 图形桌面与纯文字启动模式；图形模式自动进入 Plasma Wayland Live 会话。
- SDDM、PipeWire、NetworkManager、Firefox ESR、Discover、Dolphin、Konsole 和“落川流光”品牌体验已接入。
- Calamares 提供图形化地区、键盘、GPT/UEFI/ext4 分区、用户创建和 GRUB 安装；清空磁盘默认不选中。
- 安装器可完全断网运行，安装后清理 Calamares、Live 包、自动登录、Live sudo 和桌面安装入口。
- 当前宿主机为 macOS 26.4 arm64；ISO 在 Lima/QEMU 模拟的 Ubuntu 24.04 x86_64 构建机生成，本地 QEMU/OVMF 负责开发验收。

## 已验证

- `make test`：44 个单元测试、4 个 os-release fixture、bootstrap、清理、产品、品牌、桌面、安装器与仓库卫生契约通过。
- `make lint STRICT=1`：23 个 Shell/系统脚本、Python 配置校验、ShellCheck 与严格仓库检查通过。
- UI/UX：Logo、双主题壁纸、Plymouth、Plasma、SDDM 深色登录页、Calamares 欢迎/分区/用户/摘要/安装/完成页面、至少 44 px 交互控件和键盘焦点边框通过静态及真实帧缓冲检查。
- SFX/BGM：4 个 WAV 的 48 kHz/16-bit/mono、时长、峰值、首尾淡入淡出、SHA-256 与确定性重生成通过；会话启动音服从系统静音，BGM 预览默认关闭且不自动播放或循环。
- `make test-boot` 与 `make test-console`：UEFI 默认图形路径和纯文字路径分别检测到 `LC300A_BOOT_OK`、`LC300A_CONSOLE_OK`。
- `make test-desktop`：SDDM 自动登录、KWin Wayland、Plasma、PipeWire、WirePlumber、NetworkManager、D-Bus 和真实非黑屏帧缓冲通过。
- `make test-apps`：Konsole、Firefox、Discover、真实 HTTPS 页面与正文绘制和 9.86 秒有效 QEMU 音频输出通过，峰值 7,847、非零采样 297,248。
- `make test-installer`：完全断网安装、GPT、ext4、FAT EFI、`hwclock`、GRUB、完成页、安装后清理、移除 ISO 后启动、串口登录、SDDM 和 Plasma 通过。
- 当前 ISO 为 1,820,993,536 字节、1,617 个包，SHA-256 为 `bae3e6104d6cd2b986c20f687d01fb2e5c6f3b8d18dea4440f0347856d54eea4`。

## 已知限制

- Debian 13 原生构建机、GitHub Actions 和真实 x86_64 硬件尚未验证；macOS 上的 TCG 不能替代发布性能与硬件测试。
- 麦克风、蓝牙音频、真实声卡、睡眠与多显卡仍未验证。
- 完整中英文界面、欢迎程序、系统设置、更新程序、应用中心和系统报告属于阶段 4。
- 自有签名 APT 仓库、发布基础设施、SBOM 和完整第三方许可证材料尚未完成。

## 下一优先任务

开始阶段 4 欢迎程序、系统设置、更新程序、应用中心、系统报告、中英文界面与 Fcitx5。
