SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help doctor doctor-strict bootstrap brand-assets rootfs iso run run-uefi test test-boot test-console test-desktop test-apps test-installer lint clean release

help: ## 显示命令说明
	@printf '%s\n' \
	  'LC300A 开发命令' \
	  '' \
	  '  make doctor          诊断宿主机和依赖（不修改系统）' \
	  '  make doctor-strict   要求完整 x86_64 Linux 构建工具链' \
	  '  make bootstrap       确认后安装当前平台开发依赖' \
	  '  make brand-assets    重新生成原创品牌声音资产' \
	  '  make test            运行当前阶段测试' \
	  '  make lint            运行静态检查' \
	  '  make rootfs          构建 Live 根文件系统' \
	  '  make iso             构建当前 Live ISO' \
	  '  make run             通过 QEMU/OVMF 启动 ISO' \
	  '  make run-uefi        通过 QEMU/OVMF 启动 ISO' \
	  '  make test-boot       运行 UEFI 串口启动测试' \
	  '  make test-console    验证纯文字启动模式' \
	  '  make test-desktop    阶段 2：桌面测试' \
	  '  make test-apps       阶段 2：图形应用交互测试' \
	  '  make test-installer  阶段 3：安装器测试' \
	  '  make clean CONFIRM=1 清理 build/ 中的生成文件' \
	  '  make release         阶段 7：生成发布材料'

doctor:
	@./scripts/bootstrap/doctor.sh

doctor-strict:
	@./scripts/bootstrap/doctor.sh --strict

bootstrap:
	@./scripts/bootstrap/bootstrap.sh --install

brand-assets:
	@python3 ./scripts/build/generate_sounds.py

test:
	@./scripts/test/stage0.sh

lint:
	@./scripts/test/lint.sh

rootfs:
	@./scripts/build/live_build.sh rootfs

iso:
	@./scripts/build/live_build.sh iso

run run-uefi:
	@./scripts/test/qemu-boot.sh run

test-boot:
	@./scripts/test/qemu-boot.sh test

test-console:
	@./scripts/test/qemu-boot.sh console

test-desktop:
	@./scripts/test/qemu-boot.sh desktop

test-apps:
	@./scripts/test/qemu-boot.sh apps

test-installer release:
	@./scripts/build/stage-gate.sh "$@"

clean:
	@./scripts/clean/build.sh "$(CONFIRM)"
