# 项目状态

最后更新：2026-07-26

## 当前阶段

阶段 0：项目初始化。

## 当前事实

- 仓库已建立阶段 0 工程基线。
- 产品配置为 LC300A / 落川OS 300型，开发版本 `0.0.1-dev`。
- 产品配置具有版本、系统标识、基础套件、URL、颜色和产物路径校验。
- 仓库统一使用 LF 行尾，并拒绝常见凭据、环境文件、运行时缓存和大型系统产物进入源码树。
- bootstrap 和 doctor 只接受 Debian 13（trixie）或 Ubuntu 24.04 x86_64 构建环境。
- 已建立“落川流光”品牌基础：语义色、Logo、双主题壁纸、启动/通知/警告音及默认关闭的可选 BGM 预览。
- 当前宿主机为 macOS 26.4 arm64，不是受支持的最终 ISO 构建环境。
- 品牌资产尚未安装到 Plasma/SDDM；尚未创建 rootfs，尚未生成或启动 ISO，尚未进入阶段 1。
- 未验证 QEMU、安装器、桌面或真实硬件支持。

## 已验证

在 macOS 26.4 arm64 宿主机实际执行：

- `make help`：通过，列出全部统一命令。
- `make doctor`：通过诊断；验证 Python 3.11+/tomllib，正确报告宿主机不支持最终 ISO 构建，并指出 QEMU 缺失。
- `make lint STRICT=1`：12 个 Shell 脚本、产品配置、品牌体验、仓库卫生和 ShellCheck 全部通过。
- `make test`：16 个单元测试、4 个 os-release fixture 和构建清理契约通过；阶段 0 文件、目录、产物隔离、Git 忽略规则、LF 行尾、命令入口、ISO 阶段门禁和清理确认测试通过。
- 品牌体验检查：light/dark 文本与焦点对比度、SVG 安全和无障碍元数据、4 个 WAV 的格式/峰值/边缘/哈希及确定性重生成通过。
- 视觉 QA：使用 macOS 本地 SVG 渲染器检查 Logo 与两张 3840×2160 壁纸，通过。
- `./scripts/bootstrap/macos.sh --check`：通过，识别 Apple Silicon 并输出 x86_64 Linux 构建方案。
- `make doctor-strict`：按预期失败，拒绝将当前宿主机视为完整构建环境。
- `git diff --check`：通过。
- CI YAML 本地语法解析通过；GitHub Actions 尚未实际运行。

## 已知阻塞与限制

- 需要 Debian/Ubuntu x86_64 构建环境验证 live-build、debootstrap、OVMF 和 QEMU 工具链。
- 当前 macOS 宿主机未检测到 Docker 和 QEMU。
- CI 中的 Ubuntu bootstrap、ShellCheck 和 `make doctor-strict` 需要推送后验证，不能用本地 YAML 解析代替。
- 软件源签名密钥和发布基础设施尚未创建；这些不阻塞阶段 0。
- GPL-3.0-or-later 与 CC BY-SA 4.0 的完整许可证正文尚未从可信来源引入。

## 下一优先任务

在 Debian/Ubuntu x86_64 环境验证阶段 0 严格依赖检查，然后开始阶段 1 的最小 live-build 配置。
