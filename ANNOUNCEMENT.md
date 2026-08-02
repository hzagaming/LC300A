# 落川OS 300型 0.3.2-dev 公告

发布日期：2026-08-02

`0.3.2-dev` 是阶段 3 图形体验的可靠性补丁版本。本轮重点检查了纯文字启动、Plasma Wayland 桌面、Konsole、Firefox ESR、Discover 应用商店、Calamares 安装器、会话启动音和 BGM 默认策略。

Discover E2E 现在会等待主内容区完整绘制并检查应用卡片的色彩丰富度，不再把 `Loading…` 或只有窗口边框的画面误判为可用。音频验收在手工播放前先验证自动会话启动音，并限制自动音频的活跃时长，可同时拦截启动音失效和 BGM 意外自动播放。纯文字模式的登录欢迎语改为由产品配置动态生成，会显示当前版本及 Plasma Wayland、Firefox ESR、Discover 和 Calamares 能力。

正式候选镜像已通过 UEFI 默认图形启动、纯文字启动、Plasma Wayland 桌面、Konsole、Firefox 真实 HTTPS/DNS/证书/正文、Discover 应用卡片、自动启动音、手工音频播放、完整断网安装、Calamares 完成页、移除 ISO 后从虚拟硬盘启动、SDDM 登录和安装后 Plasma 验收。开发镜像信息：

- 文件：`LC300A-x86_64.iso`
- 大小：1,820,997,632 字节
- 软件包：1,617 个
- SHA-256：`1636f389208055e3068a9a9c61740d61ed0647c3d74b0249bddb91466b9d17d4`

这是开发版本，尚未完成真实硬件、原生 x86_64 发布性能、蓝牙/麦克风和完整中英文本地化验收。安装真实设备前请备份数据并核对目标磁盘。

旧版本公告位于 `docs/release/history/`。
