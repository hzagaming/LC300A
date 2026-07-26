# ISO 构建架构

## 范围

LC300A 生成面向 x86_64 UEFI 设备的 Debian Live ISO。阶段 0 只定义边界和构建接口；实际 live-build 配置、rootfs 和启动测试属于阶段 1。

## 构建数据流

```text
branding/product.toml
        │
        ├──> 发行版身份与产物命名
        │
distro/package-lists + distro/overlays + distro/hooks
        │
        └──> live-build 配置
                  │
                  ├──> debootstrap / Debian trixie amd64 rootfs
                  ├──> Linux + systemd + Live 用户
                  ├──> GRUB UEFI + 恢复启动项
                  └──> squashfs + ISO9660
                              │
                              └──> build/artifacts/
```

发布目录最终必须包含：

- `LC300A-x86_64.iso`
- `LC300A-x86_64.iso.sha256`
- `build-manifest.json`
- `package-manifest.txt`

## 可复现性与隔离

- 构建套件、架构和软件源必须显式配置，不读取桌面用户的 APT 状态。
- 构建缓存与生成物只写入 `build/`，不得写入仓库源文件或保存运行时用户状态。
- 构建失败必须保留明确日志并返回非零状态。
- 构建脚本不得使用未经验证的远程脚本、未知二进制或隐式 root 操作。
- 每次构建记录 Git commit、UTC 时间、宿主架构、系统版本和包清单。

## 启动与测试边界

阶段 1 使用 QEMU `q35`、OVMF 和串口日志验证 UEFI 启动。测试必须有超时，且只有检测到 systemd 目标状态和可用 shell 后才通过。macOS Apple Silicon 上的 x86_64 模拟可用于调试，但发布验收必须在 x86_64 Linux 环境重复执行。

## 后续阶段接口

- 阶段 2 在包清单和 overlay 中增加 Plasma/Wayland/SDDM，不修改阶段 1 的可启动验收。
- 阶段 3 将 Calamares 作为 Live 会话应用加入，安装用户与 Live 用户严格分离。
- Btrfs 快照与回滚保留为后续设计；首版安装目标使用 ext4。
