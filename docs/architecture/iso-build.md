# ISO 构建架构

## 范围

LC300A 生成面向 x86_64 UEFI 设备的 Debian Live ISO。阶段 1 使用 live-build 生成 rootfs，再由当前 GRUB 与 xorriso 组装 BIOS/UEFI hybrid ISO；该路径已在 Ubuntu 24.04 x86_64 构建环境和 QEMU/OVMF 中通过验收。

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
                  └──> 已清理的 chroot
                              │
                              ├──> mksquashfs
                              └──> grub-mkrescue + xorriso
                                        │
                                        └──> BIOS/UEFI hybrid ISO
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
- 只有 live-build/debootstrap/chroot 与读取完整 rootfs 的 SquashFS/统计阶段通过 `sudo` 提权，GRUB/ISO 组装、产物复制和清单生成保持普通用户权限。
- 每次构建记录 Git commit、UTC 时间、宿主架构、系统版本和包清单。

## 构建命令

```bash
make bootstrap
make doctor-strict
make rootfs
make iso
make test-boot
```

`make iso` 会生成 ISO、SHA-256、软件包清单、构建清单和完整 live-build 日志。重复构建前使用 `make clean CONFIRM=1`；该命令只清理 `build/` 中的生成项并保留受控目录。若 live-build 留下 root 所有权文件，清理命令会在明确确认后请求 sudo。

## 启动与测试边界

阶段 1 使用 QEMU `q35`、成对 OVMF CODE/VARS pflash 和串口日志验证 UEFI 启动。Live 系统进入 `multi-user.target` 后由一次性 systemd 服务验证 Live 用户、home、shell、sudo 组与 tty1，再输出 `LC300A_BOOT_OK`；测试只有检测到该标记才通过，默认超时 180 秒。macOS Apple Silicon 上的 x86_64 模拟可用于开发验收，但发布验收必须在原生 x86_64 Linux 环境执行。

## 后续阶段接口

- 阶段 2 在包清单和 overlay 中增加 Plasma/Wayland/SDDM，不修改阶段 1 的可启动验收。
- 阶段 3 将 Calamares 作为 Live 会话应用加入，安装用户与 Live 用户严格分离。
- Btrfs 快照与回滚保留为后续设计；首版安装目标使用 ext4。
