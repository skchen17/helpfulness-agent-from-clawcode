# Agent Communication Protocol (ACP) v1.0

This document defines the structural standards for communication between the **Commander (Orchestrator)** and the **Worker (Executor)** in the Hierarchical Multi-Agent System.

## 1. Overview
To prevent context explosion, all communication must be structured, minimized, and strictly typed. The goal is to ensure the Commander only receives high-level summaries while Workers receive precise, actionable instructions.

## 2. TaskPacket (Commander $\rightarrow$ Worker)
The `TaskPacket` is the payload sent to a sub-agent to initiate a task.

```json
{
  "task_id": "uuid-string",
  "parent_focus": "string", // The current active_focus of the Commander
  "objective": "string",    // Clear, single-sentence goal for this worker
  "context_snapshot": {
    "relevant_knowledge": ["node_id_1", "node_lar_2"], // Only IDs, not full content
    "environment_vars": { "key": "value" },
    "input_files": ["path/to/file"]
  },
  "constraints": [
    "string (e.g., 'Do not modify existing tests')"
  ],
  "success_criteria": {
    "observable_outcome": "string", // e.g., "A new test file exists"
    "verification_command": "string" // e.g., "pytest tests/test_new_feature.py"
  }
}
```

## 3. ResultPacket (Worker $\rightarrow$ Commander)
The `ResultPacket` is the payload sent back to the Commander upon task completion or failure.

```json
{
  "task_id": "uuid-string",
  "status": "SUCCESS | FAILED | ABORTED",
  "output_summary": "string", // A high-level summary of what was done
  "artifacts": [
    {
      "type": "file | directory | concept",
      "path": "string"
    }
  ],
  "error_log": "string | null", // Detailed error if status is FAILED
  "learned_insight": "string | null" // New knowledge to be promoted to global_context
}
```

## 4. Protocol Rules (The "Golden Rules")

1.  **Minimalism**: Workers must NOT return raw logs unless requested. Only `output_summary` is required.
2.  **Atomicity**: A TaskPacket must represent a single, atomic unit of work that can be verified independently.
3.  **No Context Leaks**: Workers should not have access to the full `global_context`. They only receive the `context_snapshot`.
4.  **Promotion**: If a Worker identifies a new pattern or error, it MUST use the `learned_insight` field to signal the Commander to update the permanent memory.

## 6. Checkpoint & Self-Preservation Protocol

To mitigate the risk of session loss due to hardware failure, power loss, or context exhaustion, the **Chronicler Agent** must be invoked periodically to create a "Session Snapshot".

### A. Trigger Conditions
1.  **User Command**: Explicit request (e.g., `"Save progress"`).
2.  **Context Pressure**: When the token usage reaches 80% of the model's effective window.
3.  **Milestone Completion**: After a significant `TaskPacket` is marked as `SUCCESS`.

### B. Snapshot Structure (`SnapshotPacket`)
The Chronicler shall generate a structured markdown file in `.memory/checkpoints/` containing:

```markdown
# Session Snapshot: [YYYY-MM-DD HH:mm:ss]

## 🎯 Current Mission Focus
[Summarize the current `active_focus`]

## ✅ Completed Milestones (Last Session)
- [ ] [Milestone 1 Description] - [Timestamp]
- [ ] [Milestone 2 Description] - [Timestamp]

## 🚧 Active Task Queue (Pending)
- [ ] [Task ID]: [Brief description of next step]

## 🧠 Synthesized Knowledge
[List key `learned_insight` or new `knowledge_nodes` discovered in this session]

## ⚠️ Known Blockers / Risks
[List any `error_log` entries that haven't been resolved via re-planning]

## 🛠️ Environment State
- Active Skills: [List of registered skills]
- Context Depth: [Current token/context pressure estimate]
```

### C. The "Chronicler" Workflow
1.  **Audit**: Read `memory_manager.py` state and `evolution.log`.
2.  **Summarize**: Compress `recent_milestones` into high-level bullet points.
3.  **Persist**: Write the Markdown snapshot to disk.
4.  **Clearance (Optional)**: If requested, prune old `recent_milestones` that have been moved to permanent `knowledge_nodes` to free up context.
