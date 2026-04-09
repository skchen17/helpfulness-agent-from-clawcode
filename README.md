# HELPFULNESS AGENT from Claw Code (Rust)

Claw Code is a Rust CLI agent runtime. The main executable is `claw`, built from
`crates/rusty-claude-cli`.

## Quick Start

```bash
cd rust

# Build CLI
cargo build -p rusty-claude-cli

# Show help
./target/debug/claw --help

# Interactive session
./target/debug/claw

# One-shot prompt
./target/debug/claw prompt "summarize this repository"
```

## Provider Configuration

Set one of the provider configurations:

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI-compatible
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="http://127.0.0.1:1234/v1"
```

You can also set these through local runtime config in `.claw/settings.local.json`
with an `env` object.
{
	"model": "####/####",
	"env": {
		"OPENAI_API_KEY": "sk-####",
		"OPENAI_BASE_URL": "http://127.0.0.1:1234/v1"
	}
}

## Useful Commands

```bash
cd rust

# Build all crates
cargo build --workspace

# Format code
cargo fmt

# Core health check commands
./target/debug/claw doctor
./target/debug/claw status
./target/debug/claw sandbox
./target/debug/claw skills
```

## Features

- Multi-provider model access
  - Anthropic API
  - OpenAI-compatible endpoints (local or hosted gateways)
- Interactive and non-interactive usage
  - REPL mode (`claw`)
  - One-shot prompt mode (`claw prompt ...`)
  - Resume previous sessions
- Built-in operational commands
  - `doctor`, `status`, `sandbox`, `skills`, `agents`, `mcp`, `login`, `logout`
- Rich tool runtime
  - File tools (`read`, `write`, `edit`, `glob`, `grep`)
  - Shell execution (`bash`)
  - Web tools (`search`, `fetch`)
  - Agent/task-oriented tool surfaces
- Runtime safety and control
  - Permission modes (`read-only`, `workspace-write`, `danger-full-access`)
  - Allowed-tools restriction support
- Extensibility surfaces
  - MCP lifecycle and tool integration
  - Plugin and skills management
- Automation-friendly output
  - Text and JSON output modes for scripting and integration

## Workspace Layout

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

## Notes

- Binary name: `claw`
- Built binary path: `rust/target/debug/claw`
- If `cargo test -p tools` fails in your environment, you can still develop and
  run the CLI with `cargo build -p rusty-claude-cli`.

## License

See license information in the repository root.
