# 落川OS 300型 0.3.4-dev 公告

发布日期：2026-08-05

`0.3.4-dev` 是阶段 3 的稳定性与验收质量更新。本轮重新构建并启动成品 ISO，逐项深查图形/纯文字启动、Plasma Wayland、Konsole、Firefox ESR、Discover 应用商店、Calamares、会话启动音和 BGM 默认策略，并人工复核桌面、应用、安装器、登录页与安装后桌面截图。

Discover 现在默认只启用 Debian PackageKit；仅当系统级或用户级配置中存在已启用的 Flatpak remote 时才自动追加 Flatpak 后端，避免空 Flatpak 配置间歇触发 `Unable to load applications`。成品镜像的 AppStream 状态识别 2,610 个软件组件，并正常显示应用卡片、分类和图标。

Firefox E2E 先独立验证 DNS、HTTPS、证书和页面正文，再直接启动单一浏览器窗口，不再重复打开相同页面。Discover E2E 改为检查整个主内容区的彩色内容比例，并加入“灰白错误页只有小块彩色错误图标”的回归用例，消除固定坐标和错误图标造成的假阳性。

最终镜像通过 52 个单元测试、4 个 os-release fixture、严格 lint/ShellCheck，以及 UEFI 图形启动、纯文字启动、Plasma 桌面、Konsole、Firefox 单标签 HTTPS 正文、Discover 应用卡片、完整断网安装、Calamares 完成页、移除 ISO 后硬盘启动、SDDM 登录和安装后 Plasma 验收。自动会话音频捕获 7.01 秒、峰值 7,848、非零采样 144,914，未检测到自动 BGM；手工播放后总捕获 9.72 秒、非零采样 295,308。开发镜像信息：

- 文件：`LC300A-x86_64.iso`
- 大小：1,808,547,840 字节
- 软件包：1,617 个
- SHA-256：`6f6ec1e635cf98ff9ea84b3348586c4b3de0308064cb9c1e59937c7f18b2a766`

这是开发版本，尚未完成真实硬件、原生 x86_64 发布性能、蓝牙/麦克风和完整中英文本地化验收。安装真实设备前请备份数据并核对目标磁盘。

旧版本公告位于 `docs/release/history/`。
