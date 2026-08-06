# 图形启动与安装

## 启动 Live 系统

准备好 `build/artifacts/LC300A-x86_64.iso` 后，可在项目目录启动 UEFI 虚拟机：

```bash
make run-uefi
```

GRUB 提供两个入口：

- `Live (图形桌面)`：默认项，3 秒后自动进入 Plasma 图形桌面。
- `Live (纯文字模式)`：用于低资源环境和排错，只启动文本控制台。

Live 文本账户为 `lc300a-live`，密码为 `live`。图形模式会自动登录，无需输入密码。

## 容量要求

- 最低磁盘：16 GiB
- 推荐磁盘：32 GiB
- 最低内存：2 GiB
- 典型安装：约 6 GiB

当前开发镜像的展开 rootfs 实测约 4.63 GiB；安装时仍应保留日志、软件缓存、更新和用户数据空间。Calamares 会检查最低磁盘与内存要求。

## 使用图形安装器

进入桌面后，双击桌面的“安装落川OS 300型”，或从应用菜单搜索同名程序。安装器将依次显示语言、地区、键盘、磁盘、用户和摘要页面。

“清空磁盘”会删除所选磁盘上的全部数据。操作真实电脑前必须备份数据，并再次核对目标磁盘；不确定时请退出安装器。当前开发版本只自动验收了 UEFI、GPT、ext4 根分区和 FAT EFI 分区。

安装器默认不选择“清空磁盘”，必须由用户明确选择后才能继续。自动验收会关闭虚拟机网络，确认安装所需内容全部来自 ISO。

安装完成后关闭系统，移除 ISO 或安装 U 盘，再从目标磁盘启动。使用安装时创建的用户和密码登录 SDDM 图形登录页。

## 桌面应用

Plasma 应用菜单和任务栏默认提供：

- Firefox ESR 浏览器
- Discover 应用商店
- Dolphin 文件管理器
- Konsole 终端

Discover 默认只启用 Debian PackageKit；检测到系统级或用户级 Flatpak remote 后才会追加 Flatpak 后端。

## 自动验收

```bash
make test-boot
make test-console
make test-desktop
make test-apps
make test-installer
```

`make test-installer` 会创建临时 32G qcow2 磁盘，在禁用虚拟机网络后执行完整安装，验证安装进度和完成页，再移除 ISO 参数，验证 UEFI 启动、分区格式、安装器清理、串口登录、SDDM 与 Plasma。macOS Apple Silicon 使用 x86_64 TCG 模拟，完整安装可能需要约一小时。
