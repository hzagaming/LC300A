# 落川OS 300型 0.3.3-dev 公告

发布日期：2026-08-03

`0.3.3-dev` 是阶段 3 图形体验与应用可用性的质量更新。本轮逐项复查了图形/纯文字启动、Plasma Wayland、Konsole、Firefox ESR、Discover 应用商店、Calamares、会话启动音和 BGM 默认策略。

Firefox ESR 首次启动不再额外打开欢迎或隐私标签，并默认关闭数据提交；实机截图只保留测试主动打开的页面。Discover 的构建流程会显式下载 Debian DEP-11 元数据、刷新 AppStream 缓存，成品镜像已识别 2,610 个软件组件并正常显示应用卡片、分类和图标。Live、构建及安装后 APT 源统一切换到清华 Debian 镜像，且不再生成 `deb-src`。

Calamares 改用无调试参数的生产启动路径，窗口扩宽至 1080 px，开发版本标题不再换行；欢迎页、分区、完整用户表单、摘要、安装和完成页均经过真实帧缓冲与人工审图。音频测试分别限制自动启动音的最长活跃时间和手工播放的最短活跃时间，避免旧启动音掩盖手工播放失败。

最终镜像通过 51 个单元测试、4 个 os-release fixture、严格 lint，以及 UEFI 图形启动、纯文字启动、Plasma 桌面、Konsole、Firefox HTTPS 正文、Discover 应用卡片、自动/手工音频、完整断网安装、Calamares 完成页、移除 ISO 后硬盘启动、SDDM 登录和安装后 Plasma 验收。开发镜像信息：

- 文件：`LC300A-x86_64.iso`
- 大小：1,808,547,840 字节
- 软件包：1,617 个
- SHA-256：`3bdd34d9774b2213c07ccaae288ffc24d48bd6ff8f4f0e3bc39e825fc9b93396`

这是开发版本，尚未完成真实硬件、原生 x86_64 发布性能、蓝牙/麦克风和完整中英文本地化验收。安装真实设备前请备份数据并核对目标磁盘。

旧版本公告位于 `docs/release/history/`。
