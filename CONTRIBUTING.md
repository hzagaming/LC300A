# 参与开发

LC300A 处于早期开发阶段。每次变更应只覆盖一个可验证工作单元，并遵守以下要求：

1. 先阅读 `PROJECT_STATE.md`、`ROADMAP.md` 和 `DECISIONS.md`。
2. 不提交凭据、构建产物、用户状态或未经许可的第三方素材。
3. 不提前声明未实际测试的功能或硬件支持。
4. 使用 `make lint` 和 `make test` 检查变更。
5. 构建相关变更还需在 Debian/Ubuntu x86_64 环境运行 `make doctor`。
6. 更新 `PROJECT_STATE.md`，记录验证命令和仍存在的限制。

提交信息建议遵循 Conventional Commits，例如 `build: add live-build configuration`。
