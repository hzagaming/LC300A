# 落川OS 300型 0.3.7-dev 公告

发布日期：2026-08-07

`0.3.7-dev` 是阶段 4 进行中的低资源体验与基础应用更新，不代表阶段 4 整体完成。本轮继续以 2 GiB 内存为最低运行口径：QEMU 默认调整为 2 GiB/6 vCPU、1280×800 virtio-vga；有 KVM 时自动使用原生加速，否则启用多线程 TCG 和 256 MiB 翻译块缓存。系统默认启用约 1 GiB zram，并关闭 Baloo 文件索引，减少低内存环境中的后台 CPU、内存和磁盘活动。

桌面新增 Ark、Gwenview、Kate、KCalc 和 Kamoso，补齐归档、图片查看、文本编辑、计算器与相机入口；应用菜单收藏和首次欢迎页同步加入常用入口。终端新增并真实执行验收 curl、wget、git、jq、htop、ripgrep、rsync、tree、zip/unzip 与 lsof。Kamoso 在当前无摄像头的虚拟机中能正确显示“未发现设备”，真实摄像头画面仍待硬件验证。

本轮深度复查修复了 QEMU 多线程 TCG 参数被错误混入 q35 机器属性、无效资源环境变量未被拒绝、Kate 使用非标准参数后提前退出、失败诊断无法读取用户服务日志等问题。首次登录欢迎程序现在等待 KSplash 退出后再显示；安装后 E2E 增加真实内容绘制门槛，不再把从登录页进入纯桌面误判为欢迎窗口。

最终镜像通过 60 个单元测试、4 个 os-release fixture、23 个 Shell/系统脚本的严格 lint 与 ShellCheck，以及 UEFI 图形启动、纯文字启动、Plasma Wayland 桌面和完整断网安装 E2E。应用验收覆盖 CLI 工具、zram、Baloo、Konsole、Dolphin、Kate、KCalc、Ark、Gwenview、Kamoso、系统设置、欢迎程序四页、Firefox HTTPS 正文与 Discover 应用卡片；安装验收覆盖 GPT/ext4/FAT EFI、Calamares 完成页、安装后清理、移除 ISO 后硬盘启动、SDDM 登录、真实首次欢迎窗口、`0600` 完成状态和不重复弹窗。

自动会话音频捕获 6.92 秒，峰值 7,843、非零采样 150,394，未检测到自动 BGM；手工试听后总捕获 15.73 秒、非零采样 844,756。开发镜像信息：

- 文件：`LC300A-x86_64.iso`
- 大小：1,980,856,320 字节
- 展开 rootfs：5,549,449,216 字节（约 5.17 GiB）
- 软件包：1,811 个
- SHA-256：`ae4ef26148ab414dfb2e039566c5995f1aba38c972ffc91af3a2754d36e074a5`

这是开发版本。阶段 4 仍未完成；真实摄像头画面、麦克风、蓝牙、真实声卡与其他实体硬件尚未验证，原生 x86_64/KVM 发布性能也未验证。安装真实设备前请备份数据并核对目标磁盘。

旧版本公告位于 `docs/release/history/`。
