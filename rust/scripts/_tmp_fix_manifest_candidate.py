from pathlib import Path

path = Path('/home/chenlu/claw-code-main/rust/crates/rusty-claude-cli/src/main.rs')
text = path.read_text(encoding='utf-8')

anchor_old = '''    if let Ok(explicit) = env::var(MEMORY_WORKER_SCRIPT_ENV) {
        let explicit = explicit.trim();
        if !explicit.is_empty() {
            let explicit_path = PathBuf::from(explicit);
            if explicit_path.is_absolute() {
                candidates.push(explicit_path);
            } else {
                if let Ok(repo_root) = find_git_root_in(cwd) {
                    candidates.push(repo_root.join(&explicit_path));
                }
                candidates.push(cwd.join(explicit_path));
            }
        }
    }

    let mut bases: Vec<PathBuf> = Vec::new();
'''
anchor_new = '''    if let Ok(explicit) = env::var(MEMORY_WORKER_SCRIPT_ENV) {
        let explicit = explicit.trim();
        if !explicit.is_empty() {
            let explicit_path = PathBuf::from(explicit);
            if explicit_path.is_absolute() {
                candidates.push(explicit_path);
            } else {
                if let Ok(repo_root) = find_git_root_in(cwd) {
                    candidates.push(repo_root.join(&explicit_path));
                }
                candidates.push(cwd.join(explicit_path));
            }
        }
    }

    candidates.push(memory_worker_script_manifest_candidate());

    let mut bases: Vec<PathBuf> = Vec::new();
'''
if anchor_old not in text:
    raise SystemExit('candidate anchor not found')
text = text.replace(anchor_old, anchor_new, 1)

resolve_old = '''fn resolve_memory_worker_script_path(cwd: &Path) -> Option<PathBuf> {
    memory_worker_script_candidates(cwd)
        .into_iter()
        .find(|path| path.is_file())
}
'''
resolve_new = '''fn memory_worker_script_manifest_candidate() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("agents")
        .join("memory_agent.py")
}

fn resolve_memory_worker_script_path(cwd: &Path) -> Option<PathBuf> {
    memory_worker_script_candidates(cwd)
        .into_iter()
        .find(|path| path.is_file())
}
'''
if resolve_old not in text:
    raise SystemExit('resolve anchor not found')
text = text.replace(resolve_old, resolve_new, 1)

import_old = 'memory_worker_script_candidates, memory_worker_sync_enabled, normalize_permission_mode,'
import_new = 'memory_worker_script_candidates, memory_worker_script_manifest_candidate,\n        memory_worker_sync_enabled, normalize_permission_mode,'
if import_old not in text:
    raise SystemExit('import anchor not found')
text = text.replace(import_old, import_new, 1)

test_old = '''        let candidates = memory_worker_script_candidates(&cwd);
        let expected = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("agents")
            .join("memory_agent.py");

        assert!(
            candidates.iter().any(|path| path == &expected),
            "manifest fallback should be present in candidate list"
        );
'''
test_new = '''        let candidates = memory_worker_script_candidates(&cwd);
        let expected = memory_worker_script_manifest_candidate();

        assert!(
            candidates.iter().any(|path| path == &expected),
            "manifest fallback should be present in candidate list"
        );
'''
if test_old not in text:
    raise SystemExit('test anchor not found')
text = text.replace(test_old, test_new, 1)

path.write_text(text, encoding='utf-8')
print('patched-manifest-candidate')
