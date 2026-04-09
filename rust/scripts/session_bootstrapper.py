import json
from datetime import datetime
from pathlib import Path

class MockTaskPacket:
    """A lightweight simulation of TaskPacket for bootstrapping without pydantic."""
    def __init__(self, task_id, parent_focus, objective, context_snapshot, constraints=None):
        self.task_id = task_id
        self.parent_focus = parent_focus
        self.objective = objective
        self.context_snapshot = context_snapshot
        self.constraints = constraints or []
        self.created_at = datetime.now().isoformat()

    def to_json(self):
        return json.dumps(self.__dict__, indent=2)

def _checkpoint_candidates(memory_root: Path) -> list[Path]:
    """Return candidates from canonical and legacy checkpoint locations."""
    canonical = sorted((memory_root / "checkpoints").glob("checkpoint_*.json"))
    legacy_root = sorted(memory_root.glob("checkpoint_*.json"))
    return canonical + legacy_root


def find_latest_checkpoint(memory_dir=".memory"):
    """Find the most recent checkpoint file from canonical and legacy paths."""
    memory_root = Path(memory_dir)
    files = [path for path in _checkpoint_candidates(memory_root) if path.is_file()]
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def _read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Checkpoint must be a JSON object: {path}")
    return payload


def _extract_metadata(checkpoint: dict) -> dict:
    metadata = checkpoint.get("context_metadata", {})
    if isinstance(metadata, dict):
        return metadata
    return {}

def bootstrap_session(checkpoint_path):
    """Bootstrap a session from a given checkpoint file."""
    if not checkpoint_path:
        print("Error: No checkpoint found.")
        return None

    checkpoint_file = Path(checkpoint_path)
    checkpoint = _read_json(checkpoint_file)
    metadata = _extract_metadata(checkpoint)

    print(f"--- Bootstrapping from: {checkpoint_file} ---")
    
    # Extract core info with backward-compatible fallbacks.
    next_point = (
        metadata.get("next_session_start_point")
        or checkpoint.get("next_instruction")
        or "No specific start point defined."
    )
    focus = (
        metadata.get("last_known_focus")
        or checkpoint.get("active_focus")
        or "General Development"
    )

    artifacts = checkpoint.get("artifacts", {})
    input_files = []
    if isinstance(artifacts, dict):
        state_file = artifacts.get("state_file")
        if state_file:
            input_files.append(str(state_file))
    
    # Prepare context snapshot (simulating the structure of ContextSnapshot)
    context_snapshot = {
        "relevant_knowledge_ids": ["checkpoint_summary"],
        "environment_vars": {"session_mode": "bootstrapped"},
        "input_files": input_files,
    }

    # Construct the TaskPacket
    # In a real scenario, we'd use UUID and pydantic models
    packet = MockTaskPacket(
        task_id=str(checkpoint.get("checkpoint_id", "bootstrapped-uuid-001")),
        parent_focus=focus,
        objective=next_point,
        context_snapshot=context_snapshot,
        constraints=["Follow the OODA loop principles"]
    )

    return packet

if __name__ == "__main__":
    checkpoint = find_latest_checkpoint()
    if checkpoint:
        packet = bootstrap_session(checkpoint)
        if packet:
            print("\n[SUCCESS] Generated TaskPacket for Claude Code:")
            print(packet.to_json())
    else:
        print("No checkpoints found in .memory/checkpoints or legacy .memory root")
