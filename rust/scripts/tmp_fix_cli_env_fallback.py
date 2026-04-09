from pathlib import Path
import re

path = Path('/home/chenlu/claw-code-main/rust/crates/rusty-claude-cli/src/main.rs')
text = path.read_text(encoding='utf-8')
orig = text

run_old = '''fn run() -> Result<(), Box<dyn std::error::Error>> {
    if let Ok(cwd) = env::current_dir() {
        apply_runtime_env_overrides_for_cwd(&cwd);
    }
'''
run_new = '''fn run() -> Result<(), Box<dyn std::error::Error>> {
    apply_runtime_env_overrides_for_cli_context();
'''
if run_old in text:
    text = text.replace(run_old, run_new, 1)

helper_pattern = re.compile(
    r"fn apply_runtime_env_overrides_for_cwd\(cwd: &Path\) \{[\s\S]*?\n\}\n\n#\[derive\(Debug, Clone, PartialEq, Eq\)\]",
    re.MULTILINE,
)
helper_replacement = '''fn apply_runtime_env_overrides_for_cwd(cwd: &Path) {
    let loader = ConfigLoader::default_for(cwd);
    let Ok(runtime_config) = loader.load() else {
        return;
    };
    let Some(config_env) = runtime_config
        .get("env")
        .and_then(|value| value.as_object())
    else {
        return;
    };

    // Keep explicit shell env highest-priority, but allow config env to fill missing values.
    for (key, value) in config_env {
        let Some(value) = value.as_str() else {
            continue;
        };
        let should_set = match env::var(key) {
            Ok(existing) => existing.trim().is_empty(),
            Err(_) => true,
        };
        if should_set {
            env::set_var(key, value);
        }
    }
}

fn apply_runtime_env_overrides_for_cli_context() {
    let base_dir = resolve_runtime_config_base_dir_for_cli_env().or_else(|| env::current_dir().ok());
    if let Some(base_dir) = base_dir {
        apply_runtime_env_overrides_for_cwd(&base_dir);
    }
}

fn resolve_runtime_config_base_dir_for_cli_env() -> Option<PathBuf> {
    // Prefer executable ancestry first so running the built binary from an
    // unrelated cwd (for example `~/`) still discovers the project-local
    // `.claw/settings.local.json` next to that binary.
    if let Some(base_dir) = env::current_exe()
        .ok()
        .as_deref()
        .and_then(find_runtime_config_base_from_path)
    {
        return Some(base_dir);
    }

    let cwd = env::current_dir().ok()?;
    find_runtime_config_base_from_path(&cwd)
}

fn find_runtime_config_base_from_path(path: &Path) -> Option<PathBuf> {
    let base = if path.is_file() { path.parent()? } else { path };
    base
        .ancestors()
        .find(|candidate| has_project_runtime_config(candidate))
        .map(Path::to_path_buf)
}

fn has_project_runtime_config(path: &Path) -> bool {
    path.join(".claw.json").is_file()
        || path.join(".claw").join("settings.json").is_file()
        || path.join(".claw").join("settings.local.json").is_file()
}

#[derive(Debug, Clone, PartialEq, Eq)]'''

text, helper_count = helper_pattern.subn(helper_replacement, text, count=1)

marker = '''    #[test]
    fn load_runtime_oauth_config_for_returns_none_without_project_config() {
'''
insert_tests = '''    #[test]
    fn finds_runtime_config_base_from_nested_directory() {
        let root = temp_dir();
        let project = root.join("project");
        let nested = project.join("apps").join("demo");
        std::fs::create_dir_all(project.join(".claw")).expect("project config dir should exist");
        std::fs::create_dir_all(&nested).expect("nested dir should exist");
        std::fs::write(project.join(".claw").join("settings.local.json"), "{}")
            .expect("local settings should write");

        let resolved = super::find_runtime_config_base_from_path(&nested);

        std::fs::remove_dir_all(root).expect("temp root should clean up");
        assert_eq!(resolved, Some(project));
    }

    #[test]
    fn finds_runtime_config_base_from_file_path() {
        let root = temp_dir();
        let project = root.join("project");
        let binary = project.join("target").join("debug").join("claw");
        std::fs::create_dir_all(project.join(".claw")).expect("project config dir should exist");
        std::fs::create_dir_all(binary.parent().expect("binary parent"))
            .expect("binary parent should exist");
        std::fs::write(project.join(".claw").join("settings.json"), "{}")
            .expect("project settings should write");
        std::fs::write(&binary, "#!/bin/sh\\n")
            .expect("fake binary should write");

        let resolved = super::find_runtime_config_base_from_path(&binary);

        std::fs::remove_dir_all(root).expect("temp root should clean up");
        assert_eq!(resolved, Some(project));
    }

'''
if marker in text and 'fn finds_runtime_config_base_from_nested_directory()' not in text:
    text = text.replace(marker, insert_tests + marker, 1)

if text == orig:
    raise SystemExit('no changes applied')

path.write_text(text, encoding='utf-8')
print('patched', helper_count)
