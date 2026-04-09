from pathlib import Path

path = Path('/home/chenlu/claw-code-main/rust/crates/rusty-claude-cli/src/main.rs')
text = path.read_text(encoding='utf-8')

old = 'memory_worker_sync_enabled, normalize_permission_mode'
new = 'memory_worker_sync_enabled, resolve_memory_worker_script_path, MEMORY_WORKER_SCRIPT_ENV,\n        normalize_permission_mode'
if old not in text:
    raise SystemExit('import token not found')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('patched-imports')
