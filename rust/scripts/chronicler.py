import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.memory_manager import MemoryManager
except ImportError:
    from memory_manager import MemoryManager


class Chronicler:
    def __init__(self, memory_manager: MemoryManager):
        self.mm = memory_manager
        self.memory_root = Path(self.mm.memory_root)
        self.checkpoint_dir = Path(self.mm.memory_root) / "checkpoints"
        self.archive_checkpoint_dir = Path(self.mm.archive_dir) / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.archive_checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _token(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def _parse_active_tasks(self, state: dict) -> list[str]:
        tasks_value = state.get("global_context", {}).get("active_tasks", "")
        if isinstance(tasks_value, list):
            cleaned = [str(item).strip() for item in tasks_value if str(item).strip()]
            return cleaned[:10]

        tasks_text = str(tasks_value).strip()
        if not tasks_text:
            return []

        lines: list[str] = []
        for raw_line in tasks_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = line.lstrip("- ")
            line = line.lstrip("[]")
            line = line.strip()
            if line:
                lines.append(line)
        if lines:
            return lines[:10]
        return [tasks_text[:200]]

    def _collect_learned_insights(self, state: dict) -> list[str]:
        insights: list[str] = []
        last_result = state.get("last_result", {})
        if isinstance(last_result, dict):
            learned = last_result.get("learned_insight")
            if learned:
                insights.append(str(learned).strip())
        return [item for item in insights if item][:5]

    def _render_snapshot_markdown(
        self,
        created_at: str,
        focus: str,
        milestones: list[str],
        tasks: list[str],
        insights: list[str],
        error_log: str,
        skills: list[str],
    ) -> str:
        lines = [
            f"# Session Snapshot: {created_at}",
            "",
            "## Current Mission Focus",
            focus,
            "",
            "## Completed Milestones",
        ]

        if milestones:
            lines.extend(f"- [x] {item}" for item in milestones)
        else:
            lines.append("- No recent milestones found.")

        lines.extend(["", "## Active Task Queue"])
        if tasks:
            lines.extend(f"- [ ] {item}" for item in tasks)
        else:
            lines.append("- No active tasks detected.")

        lines.extend(["", "## Synthesized Knowledge"])
        if insights:
            lines.extend(f"- {item}" for item in insights)
        else:
            lines.append("- No new insights recorded in this session.")

        lines.extend(
            [
                "",
                "## Known Blockers / Risks",
                f"- {error_log}",
                "",
                "## Environment State",
                f"- Active Skills: {', '.join(skills) if skills else 'None'}",
                "- Context Depth: High (Checkpoint Triggered)",
            ]
        )

        return "\n".join(lines) + "\n"

    def create_snapshot(self) -> Path:
        now = datetime.now(timezone.utc)
        token = self._token()
        checkpoint_name = f"checkpoint_{token}"
        checkpoint_path = self.checkpoint_dir / f"{checkpoint_name}.json"
        snapshot_path = self.archive_checkpoint_dir / f"{checkpoint_name}.md"

        state = self.mm.get_all_state()
        global_context = state.get("global_context", {})

        active_focus = str(global_context.get("active_focus") or "Unknown")
        next_instruction = str(global_context.get("next_instruction") or active_focus)
        milestones = [str(item) for item in state.get("recent_milestones", []) if str(item).strip()]
        milestones = milestones[-5:]
        active_tasks = self._parse_active_tasks(state)
        learned_insights = self._collect_learned_insights(state)
        error_log = str(state.get("last_error") or "No recent errors reported.")
        skills = [str(item) for item in global_context.get("active_skills", []) if str(item).strip()]

        snapshot_content = self._render_snapshot_markdown(
            created_at=now.isoformat(),
            focus=active_focus,
            milestones=milestones,
            tasks=active_tasks,
            insights=learned_insights,
            error_log=error_log,
            skills=skills,
        )
        snapshot_path.write_text(snapshot_content, encoding="utf-8")

        checkpoint_payload = {
            "version": "1.0",
            "checkpoint_id": checkpoint_name,
            "created_at": now.isoformat(),
            "context_metadata": {
                "last_known_focus": active_focus,
                "next_session_start_point": next_instruction,
                "active_tasks": active_tasks,
                "recent_milestones": milestones,
            },
            "diagnostics": {
                "last_error": error_log,
                "active_skills": skills,
                "learned_insights": learned_insights,
            },
            "artifacts": {
                "state_file": str(self.mm.state_path),
                "snapshot_markdown": str(snapshot_path),
            },
        }
        checkpoint_path.write_text(
            json.dumps(checkpoint_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        self.mm.log_event(f"Checkpoint created: {checkpoint_path.name}")
        print(f"✅ Checkpoint created at: {checkpoint_path}")
        print(f"✅ Snapshot archived at: {snapshot_path}")
        return checkpoint_path

if __name__ == "__main__":
    try:
        mm = MemoryManager()
        chronicler = Chronicler(mm)
        chronicler.create_snapshot()
    except Exception as e:
        print(f"❌ Failed to run Chronicler prototype: {e}")

