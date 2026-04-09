# Code Review Standard Operating Procedure (SOP)

## 1. OBJECTIVE
To ensure all code changes are verified for correctness, safety, performance, and consistency with the existing codebase and project standards.

## 2. PRE-REVIEW CHECKLIST
Before analyzing the code, verify the following:
- [ ] **Context Alignment**: Does the change align with the `active_focus`?
- [ ] **Test Coverage**: Are there corresponding tests in `tests/`? Do they pass?
- [ ] **Scope Check**: Is the change tightly scoped to the intended task?

## 3. REVIEW STEPS

### STEP 1: Impact Analysis
- Identify all files modified.
- Determine if the changes affect existing APIs, data structures, or public interfaces.
- Check for potential side effects in dependent modules.

### STEP 2: Static Analysis & Quality
- **Syntax & Type Safety**: Ensure no Rust compilation errors (run `cargo check`).
- **Complexity**: Identify overly complex functions or logic branches that may be error-prone.
- **Error Handling**: Verify that all error paths are handled correctly and that errors are propagated using appropriate methods (e.g., `Result`, `anyhow`).

### STEP 3: Security & Safety
- **Memory Safety**: Check for any potential use of `unsafe` blocks and ensure they are justified and safe.
- **Input Validation**: Ensure all external inputs are properly validated.
- **Resource Management**: Verify that file handles, network sockets, and memory allocations are correctly managed.

### STEP 4: Consistency & Style
- **Linting**: Run `cargo clippy` to ensure compliance with project linting rules.
- **Formatting**: Ensure code follows the project's `cargo fmt` standards.
- **Documentation**: Check that any new or changed logic is accompanied by appropriate doc comments (`///`).

## 4. POST-REVIEW ACTIONS
- If issues are found: Document them clearly and suggest specific fixes.
- If passed: Record the successful review in the `evolution.log`.
