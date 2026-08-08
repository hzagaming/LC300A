# 项目状态

最后更新：2026-08-07

## 当前阶段

阶段 4：桌面体验和系统应用（进行中）；首次登录、容量透明度、低内存策略与基础应用增量完成。

## 当前事实

- 产品为 LC300A / 落川OS 300型，开发版本 `0.3.7-dev`，基于 Debian 13（trixie）amd64。
- 产品统一要求最低磁盘 16 GiB、推荐磁盘 32 GiB、最低内存 2 GiB、典型安装约 6 GiB；本轮展开 rootfs 实测 5,549,449,216 字节（约 5.17 GiB）。
- ISO 提供 UEFI/GRUB 图形桌面与纯文字启动模式；图形模式自动进入 Plasma Wayland Live 会话。
- SDDM、PipeWire、NetworkManager、Firefox ESR、Discover、Dolphin、Konsole、Kate、KCalc、Ark、Gwenview、Kamoso 和“落川流光”品牌体验已接入。
- 默认关闭 Baloo 文件索引并启用 zram；curl、wget、git、jq、htop、ripgrep、rsync、tree、zip/unzip 与 lsof 已预装并经过真实命令验收。
- Calamares 提供图形化地区、键盘、GPT/UEFI/ext4 分区、用户创建和 GRUB 安装；清空磁盘默认不选中。
- 安装器可完全断网运行，安装后清理 Calamares、Live 包、自动登录、Live sudo 和桌面安装入口。
- 安装后首次登录显示 Qt 6/QML 四步欢迎程序和容量信息；Live 环境不自动显示，完成状态以 `0600` 保存且后续不重复弹窗。
- 欢迎程序提供系统设置、Discover、支持页与手工声音试听；URI 动作采用严格白名单，无提权或 shell 拼接。
- 当前宿主机为 macOS 26.4 arm64；ISO 在 Lima/QEMU 模拟的 Ubuntu 24.04 x86_64 构建机生成，本地 QEMU/OVMF 负责开发验收。

## 已验证

- `make test`：60 个单元测试、4 个 os-release fixture、bootstrap、清理、产品、品牌、桌面、欢迎程序、安装器与仓库卫生契约通过。
- `make lint STRICT=1`：23 个 Shell/系统脚本、Python 配置校验、ShellCheck 与严格仓库检查通过。
- UI/UX：Logo、双主题壁纸、Plymouth、Plasma、SDDM 深色登录页、欢迎程序四页及 16/32/2/约 6 GiB 容量卡片、Kate、KCalc、Ark、Gwenview、Kamoso 无设备界面、Firefox HTTPS 正文、Discover 应用卡片，以及 Calamares 生产界面的欢迎/分区/完整用户表单/摘要/安装/完成页面通过真实帧缓冲与人工审图。
- SFX/BGM：4 个 WAV 的 48 kHz/16-bit/mono、时长、峰值、首尾淡入淡出、SHA-256 与确定性重生成通过；自动启动音最长活跃时间与手工播放最短活跃时间分别验收，BGM 预览默认关闭且不自动播放或循环。
- `make test-boot` 与 `make test-console`：UEFI 默认图形路径和纯文字路径分别检测到 `LC300A_BOOT_OK`、`LC300A_CONSOLE_OK`。
- `make test-desktop`：SDDM 自动登录、KWin Wayland、Plasma、PipeWire、WirePlumber、NetworkManager、D-Bus 和真实非黑屏帧缓冲通过。
- `make test-apps`：CLI 工具真实执行、zram、Baloo 禁用状态，以及 Konsole、Dolphin、Kate、KCalc、Ark、Gwenview、Kamoso、系统设置、欢迎程序四页、Firefox、Discover 和 URI 动作通过；自动阶段捕获 6.92 秒有效 WAV，峰值 7,843、非零采样 150,394，且未检测到自动 BGM；手工环境音后总捕获 15.73 秒、非零采样 844,756。
- 成品 chroot 的 AppStream 状态识别 2,610 个软件组件、3 个软件目录源和 3 个图标集；Discover 默认只使用 PackageKit，配置系统级或用户级 Flatpak remote 后自动追加 Flatpak 后端。
- `make test-installer`：16 GiB/2 GiB 安装门槛配置、无调试参数的完整断网安装、GPT、ext4、FAT EFI、`hwclock`、GRUB、稳定完成页、安装后清理、移除 ISO 后启动、串口登录、SDDM、真实首次欢迎窗口、`0600` 完成状态与不重复弹窗完整通过。
- 当前 ISO 为 1,980,856,320 字节、1,811 个包，SHA-256 为 `ae4ef26148ab414dfb2e039566c5995f1aba38c972ffc91af3a2754d36e074a5`。

## 已知限制

- Debian 13 原生构建机、GitHub Actions 和真实 x86_64 硬件尚未验证；macOS 上的 TCG 不能替代发布性能与硬件测试。
- 真实摄像头画面、麦克风、蓝牙音频、真实声卡、睡眠与多显卡仍未验证。
- 阶段 4 尚未完成定制系统设置、更新程序、应用中心、系统报告和完整中英文界面。
- 自有签名 APT 仓库、发布基础设施、SBOM 和完整第三方许可证材料尚未完成。

## 下一优先任务

继续阶段 4：定制系统设置、更新程序、应用中心、系统报告、中英文界面与 Fcitx5。
