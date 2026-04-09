from pathlib import Path

path = Path('/home/chenlu/claw-code-main/rust/crates/rusty-claude-cli/src/main.rs')
text = path.read_text(encoding='utf-8')

old_const = 'const MEMORY_MAX_MILESTONES: usize = 12;\nconst MEMORY_WORKER_SCRIPT_PATH: &str = "rust/agents/memory_agent.py";'
new_const = 'const MEMORY_MAX_MILESTONES: usize = 12;\nconst MEMORY_WORKER_SCRIPT_ENV: &str = "CLAW_MEMORY_AGENT_SCRIPT";\nconst MEMORY_WORKER_SCRIPT_PATH: &str = "rust/agents/memory_agent.py";'
if old_const not in text:
    raise SystemExit('const anchor not found')
text = text.replace(old_const, new_const, 1)

old_resolver_call = '''    let cwd = env::current_dir()?;
    let script_path = resolve_memory_worker_script_path(&cwd)
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "memory worker script not found"))?;
    let python = resolve_memory_worker_python()
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "python interpreter not found"))?;
'''
new_resolver_call = '''    let cwd = env::current_dir()?;
    let script_candidates = memory_worker_script_candidates(&cwd);
    let script_path = script_candidates
        .iter()
        .find(|path| path.is_file())
        .cloned()
        .ok_or_else(|| {
            let checked = if script_candidates.is_empty() {
                "<none>".to_string()
            } else {
                script_candidates
                    .iter()
                    .take(10)
                    .map(|path| path.display().to_string())
                    .collect::<Vec<_>>()
                    .join(", ")
            };
            io::Error::new(
                io::ErrorKind::NotFound,
                format!(
                    "memory worker script not found (env {MEMORY_WORKER_SCRIPT_ENV}, checked: {checked})"
                ),
            )
        })?;
    let python = resolve_memory_worker_python()
        .ok_or_else(|| io::Error::new(io::ErrorKind::NotFound, "python interpreter not found"))?;
'''
if old_resolver_call not in text:
    raise SystemExit('resolver call anchor not found')
text = text.replace(old_resolver_call, new_resolver_call, 1)

old_resolve_fn = '''fn resolve_memory_worker_script_path(cwd: &Path) -> Option<PathBuf> {
    let repo_root = find_git_root_in(cwd).unwrap_or_else(|_| cwd.to_path_buf());
    let fallback_repo_root = cwd.to_path_buf();
    [
        repo_root.join(MEMORY_WORKER_SCRIPT_PATH),
        repo_root.join("agents").join("memory_agent.py"),
        fallback_repo_root.join(MEMORY_WORKER_SCRIPT_PATH),
        fallback_repo_root.join("agents").join("memory_agent.py"),
    ]
    .into_iter()
    .find(|path| path.is_file())
}
'''
new_resolve_fn = '''fn memory_worker_script_candidates(cwd: &Path) -> Vec<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();

    if let Ok(explicit) = env::var(MEMORY_WORKER_SCRIPT_ENV) {
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
    if let Ok(repo_root) = find_git_root_in(cwd) {
        bases.push(repo_root);
    }
    bases.extend(cwd.ancestors().take(8).map(Path::to_path_buf));

    for base in bases {
        candidates.push(base.join(MEMORY_WORKER_SCRIPT_PATH));
        candidates.push(base.join("agents").join("memory_agent.py"));
    }

    let mut deduped: Vec<PathBuf> = Vec::new();
    for path in candidates {
        if !deduped.iter().any(|existing| existing == &path) {
            deduped.push(path);
        }
    }
    deduped
}

fn resolve_memory_worker_script_path(cwd: &Path) -> Option<PathBuf> {
    memory_worker_script_candidates(cwd)
        .into_iter()
        .find(|path| path.is_file())
}
'''
if old_resolve_fn not in text:
    raise SystemExit('resolve function anchor not found')
text = text.replace(old_resolve_fn, new_resolve_fn, 1)

old_test_anchor = '''    #[test]
    fn memory_worker_respects_disable_flag() {
        let _guard = env_lock();
        let original = std::env::var("CLAW_ENABLE_MEMORY_WORKER").ok();
        std::env::set_var("CLAW_ENABLE_MEMORY_WORKER", "false");
        assert!(!memory_worker_sync_enabled());
        match original {
            Some(value) => std::env::set_var("CLAW_ENABLE_MEMORY_WORKER", value),
            None => std::env::remove_var("CLAW_ENABLE_MEMORY_WORKER"),
        }
    }

    #[test]
    fn config_report_uses_sectioned_layout() {
'''
new_test_anchor = '''    #[test]
    fn memory_worker_respects_disable_flag() {
        let _guard = env_lock();
        let original = std::env::var("CLAW_ENABLE_MEMORY_WORKER").ok();
        std::env::set_var("CLAW_ENABLE_MEMORY_WORKER", "false");
        assert!(!memory_worker_sync_enabled());
        match original {
            Some(value) => std::env::set_var("CLAW_ENABLE_MEMORY_WORKER", value),
            None => std::env::remove_var("CLAW_ENABLE_MEMORY_WORKER"),
        }
    }

    #[test]
    fn memory_worker_script_resolution_prefers_explicit_env_path() {
        let _guard = env_lock();
        let temp_root = temp_dir();
        fs::create_dir_all(&temp_root).expect("temp root");
        let script_path = temp_root.join("custom_memory_agent.py");
        fs::write(&script_path, "print('ok')\\n").expect("write custom script");

        let original = std::env::var(MEMORY_WORKER_SCRIPT_ENV).ok();
        std::env::set_var(MEMORY_WORKER_SCRIPT_ENV, script_path.as_os_str());

        let resolved = resolve_memory_worker_script_path(&temp_root).expect("script should resolve");
        assert_eq!(resolved, script_path);

        match original {
            Some(value) => std::env::set_var(MEMORY_WORKER_SCRIPT_ENV, value),
            None => std::env::remove_var(MEMORY_WORKER_SCRIPT_ENV),
        }
        fs::remove_dir_all(temp_root).expect("cleanup temp dir");
    }

    #[test]
    fn memory_worker_script_resolution_scans_parent_ancestors() {
        let _guard = env_lock();
        let original = std::env::var(MEMORY_WORKER_SCRIPT_ENV).ok();
        std::env::remove_var(MEMORY_WORKER_SCRIPT_ENV);

        let temp_root = temp_dir();
        let nested = temp_root.join("child").join("deep");
        let agents_dir = temp_root.join("agents");
        fs::create_dir_all(&nested).expect("nested dir");
        fs::create_dir_all(&agents_dir).expect("agents dir");

        let script_path = agents_dir.join("memory_agent.py");
        fs::write(&script_path, "print('ok')\\n").expect("write agent script");

        let resolved =
            resolve_memory_worker_script_path(&nested).expect("ancestor script should resolve");
        assert_eq!(resolved, script_path);

        match original {
            Some(value) => std::env::set_var(MEMORY_WORKER_SCRIPT_ENV, value),
            None => std::env::remove_var(MEMORY_WORKER_SCRIPT_ENV),
        }
        fs::remove_dir_all(temp_root).expect("cleanup temp dir");
    }

    #[test]
    fn config_report_uses_sectioned_layout() {
'''
if old_test_anchor not in text:
    raise SystemExit('test anchor not found')
text = text.replace(old_test_anchor, new_test_anchor, 1)

path.write_text(text, encoding='utf-8')
print('patched')
