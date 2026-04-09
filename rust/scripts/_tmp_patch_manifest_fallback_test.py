from pathlib import Path

path = Path('/home/chenlu/claw-code-main/rust/crates/rusty-claude-cli/src/main.rs')
text = path.read_text(encoding='utf-8')

if 'fn memory_worker_candidates_include_manifest_fallback()' not in text:
    import_old = 'memory_worker_sync_enabled, normalize_permission_mode, parse_args, parse_git_status_branch,'
    import_new = 'memory_worker_script_candidates, memory_worker_sync_enabled, normalize_permission_mode,\n        parse_args, parse_git_status_branch,'
    if import_old not in text:
        raise SystemExit('import anchor not found')
    text = text.replace(import_old, import_new, 1)

    insert_anchor = '    #[test]\n    fn config_report_uses_sectioned_layout() {'
    insert_block = '''    #[test]
    fn memory_worker_candidates_include_manifest_fallback() {
        let _guard = env_lock();
        let original = std::env::var(MEMORY_WORKER_SCRIPT_ENV).ok();
        std::env::remove_var(MEMORY_WORKER_SCRIPT_ENV);

        let cwd = temp_dir();
        fs::create_dir_all(&cwd).expect("temp cwd");

        let candidates = memory_worker_script_candidates(&cwd);
        let expected = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("..")
            .join("agents")
            .join("memory_agent.py");

        assert!(
            candidates.iter().any(|path| path == &expected),
            "manifest fallback should be present in candidate list"
        );

        match original {
            Some(value) => std::env::set_var(MEMORY_WORKER_SCRIPT_ENV, value),
            None => std::env::remove_var(MEMORY_WORKER_SCRIPT_ENV),
        }
        fs::remove_dir_all(cwd).expect("cleanup temp cwd");
    }

'''
    if insert_anchor not in text:
        raise SystemExit('insert anchor not found')
    text = text.replace(insert_anchor, insert_block + insert_anchor, 1)

path.write_text(text, encoding='utf-8')
print('patched-manifest-test')
