# HELPFULNESS AGENT from Claw Code (Rust)

Claw Code 是一个 Rust CLI 代理运行时。主可执行文件是 `claw`，源代码位于 `crates/rusty-claude-cli`。

## 快速开始

```bash
cd rust

# 构建 CLI
cargo build -p rusty-claude-cli

# 显示帮助
./target/debug/claw --help

# 交互式会话
./target/debug/claw

# 一次性提示词
./target/debug/claw prompt "summarize this repository"
```

## 提供商配置

设置以下任一提供商配置：

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI 兼容
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="http://127.0.0.1:1234/v1"
```

您也可以通过 `.claw/settings.local.json` 中的本地运行时配置设置这些，使用 `env` 对象：
```json
{
	"model": "####/####",
	"env": {
		"OPENAI_API_KEY": "sk-####",
		"OPENAI_BASE_URL": "http://127.0.0.1:1234/v1"
	}
}
```

## 常用命令

```bash
cd rust

# 构建所有 crates
cargo build --workspace

# 格式化代码
cargo fmt

# 核心健康检查命令
./target/debug/claw doctor
./target/debug/claw status
./target/debug/claw sandbox
./target/debug/claw skills
```

## 功能特性

- 多提供商模型访问
  - Anthropic API
  - OpenAI 兼容端点（本地或托管网关）
- 交互式和非交互式使用
  - REPL 模式 (`claw`)
  - 一次性提示词模式 (`claw prompt ...`)
  - 恢复之前的会话
- 内置操作命令
  - `doctor`, `status`, `sandbox`, `skills`, `agents`, `mcp`, `login`, `logout`
- 丰富的工具运行时
  - 文件工具 (`read`, `write`, `edit`, `glob`, `grep`)
  - Shell 执行 (`bash`)
  - Web 工具 (`search`, `fetch`)
  - 面向代理/任务的工具界面
- 运行时安全与控制
  - 权限模式 (`read-only`, `workspace-write`, `danger-full-access`)
  - 支持 allowed-tools 限制
- 可扩展性界面
  - MCP 生命周期和工具集成
  - 插件和技能管理
- 自动化友好输出
  - 文本和 JSON 输出模式，用于脚本和集成

## 工作区布局

```text
rust/
├── Cargo.toml
├── Cargo.lock
├── agents/
├── prompts/
├── scripts/
└── crates/
    ├── api/
    ├── commands/
    ├── compat-harness/
    ├── mock-anthropic-service/
    ├── plugins/
    ├── runtime/
    ├── rusty-claude-cli/
    ├── telemetry/
    └── tools/
```

## 注意事项

- 二进制文件名：`claw`
- 构建后的二进制文件路径：`rust/target/debug/claw`
- 如果 `cargo test -p tools` 在您的环境中失败，您仍然可以使用 `cargo build -p rusty-claude-cli` 来开发和运行 CLI。

## 许可证

请参阅仓库根目录中的许可证信息。
