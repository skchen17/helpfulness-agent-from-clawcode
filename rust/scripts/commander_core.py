from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

RUST_ROOT = Path(__file__).resolve().parents[1]
if str(RUST_ROOT) not in sys.path:
    sys.path.insert(0, str(RUST_ROOT))

try:
    from scripts.memory_manager import MemoryManager
except ImportError:
    from memory_manager import MemoryManager

try:
    from agents.protocol import TaskPacket
except ImportError:
    TaskPacket = None


class CommanderCore:
    """Implements a lightweight Observe-Orient-Decide-Act control loop."""

    def __init__(self, memory_root: str = ".memory"):
        self.mm = MemoryManager(memory_root=memory_root)
        self.memory_root = Path(memory_root)
        self.active_task_packet: TaskPacket | dict[str, Any] | None = None

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        self.mm.log_event(message)

    def _active_task_path(self) -> Path:
        return self.memory_root / "active_task.json"

    def _try_load_task_packet(self) -> bool:
        task_file = self._active_task_path()
        if not task_file.exists():
            self.active_task_packet = None
            return False

        try:
            payload = json.loads(task_file.read_text(encoding="utf-8"))
            if TaskPacket is not None and isinstance(payload, dict):
                self.active_task_packet = TaskPacket(**payload)
            else:
                self.active_task_packet = payload
            self.log(f"Loaded active task packet from {task_file}")
            return True
        except Exception as exc:
            self.active_task_packet = None
            self.log(f"Failed to load active task packet: {exc}")
            return False

    def _task_objective(self) -> str:
        packet = self.active_task_packet
        if packet is None:
            return ""
        if hasattr(packet, "objective"):
            return str(packet.objective)
        if isinstance(packet, dict):
            if "objective" in packet:
                return str(packet["objective"])
            metadata = packet.get("context_metadata", {})
            if isinstance(metadata, dict):
                return str(metadata.get("next_session_start_point", ""))
        return ""

    def observe(self) -> str:
        self.mm.load_state()
        context = self.mm.get_startup_context()
        self._try_load_task_packet()
        self.log("Observe phase complete")
        return context

    def orient(self, context: str) -> bool:
        _ = context
        state = self.mm.load_state()
        milestones = state.get("recent_milestones", [])
        has_focus = bool(state.get("global_context", {}).get("active_focus"))
        needs_checkpoint = has_focus and not milestones
        if self.active_task_packet is not None:
            self.log(f"Detected active task objective: {self._task_objective()}")
        self.log(f"Orient phase complete (needs_checkpoint={needs_checkpoint})")
        return needs_checkpoint

    def decide(self, needs_checkpoint: bool) -> str:
        if needs_checkpoint:
            return "TRIGGER_CHRONIC_CHECKPOINT"
        if self.active_task_packet is not None:
            return "PROCEED_TASK"
        return "PROCEED"

    def _run_chronicler(self) -> bool:
        script = Path("scripts") / "chronicler.py"
        if not script.exists():
            self.log("Chronicler script not found")
            return False
        try:
            subprocess.run([sys.executable, str(script)], check=True)
            return True
        except subprocess.CalledProcessError as exc:
            self.log(f"Chronicler failed: {exc}")
            return False

    def _execute_skill(self, skill_name: str, objective: str) -> bool:
        try:
            if skill_name != "code_executor":
                self.log(f"No implementation for skill: {skill_name}")
                return False

            from agents.skills.code_executor import CodeExecutor

            executor = CodeExecutor(memory_manager=self.mm)
            success = executor.execute(objective)
            if success:
                self.log("Skill code_executor completed successfully")
            else:
                self.log("Skill code_executor failed")
            return success
        except Exception as exc:
            self.log(f"Skill execution error ({skill_name}): {exc}")
            return False

    def _execute_task_objective(self) -> bool:
        objective = self._task_objective().strip()
        if not objective:
            self.log("Active task has no objective")
            return False

        lowered = objective.lower()
        if lowered.startswith("run:") or "code" in lowered or "implementation" in lowered:
            return self._execute_skill("code_executor", objective)

        self.log("No matching skill route; task marked as handled without execution")
        return True

    def act(self, action: str) -> bool:
        if action == "TRIGGER_CHRONIC_CHECKPOINT":
            self.log("Executing checkpoint action")
            return self._run_chronicler()

        if action == "PROCEED_TASK":
            self.log(f"Executing task objective: {self._task_objective()}")
            return self._execute_task_objective()

        self.log("Proceeding without task-specific action")
        return True

    def run_loop(self) -> bool:
        context = self.observe()
        needs_checkpoint = self.orient(context)
        action = self.decide(needs_checkpoint)
        self.log(f"Decision: {action}")
        return self.act(action)


if __name__ == "__main__":
    commander = CommanderCore()
    ok = commander.run_loop()
    raise SystemExit(0 if ok else 1)
