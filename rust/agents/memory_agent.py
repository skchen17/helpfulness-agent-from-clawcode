from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


RUST_ROOT = Path(__file__).resolve().parents[1]
for import_root in (RUST_ROOT, RUST_ROOT / "agents", RUST_ROOT / "scripts"):
    root_text = str(import_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

try:
    from agents.base_agent import BaseAgent
    from agents.protocol import Artifact, ResultPacket, TaskPacket
except ImportError:
    from base_agent import BaseAgent
    from protocol import Artifact, ResultPacket, TaskPacket

try:
    from scripts.context_retriever import ContextRetriever
    from scripts.memory_manager import MemoryManager
except ImportError:
    from context_retriever import ContextRetriever
    from memory_manager import MemoryManager


class MemoryAgent(BaseAgent):
    """Worker that records and retrieves long-term memory entries."""

    MAX_RECENT_MILESTONES = 12

    def __init__(self, memory_root: str = ".memory"):
        super().__init__("MemoryExpert")
        self.manager = MemoryManager(memory_root)
        self.retriever = ContextRetriever(memory_root)

    def log(self, message: str) -> None:
        print(f"[{self.name}] {message}", file=sys.stderr)

    def _parse_store_command(self, objective: str) -> tuple[str, str] | None:
        match = re.match(r"^(store|record)\s+([^:]+):\s*(.+)$", objective, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        node = match.group(2).strip()
        content = match.group(3).strip()
        if not node or not content:
            return None
        return node, content

    def _parse_retrieval_query(self, objective: str) -> str:
        cleaned = objective.strip()
        lowered = cleaned.lower()
        for prefix in ("retrieve", "search"):
            if lowered.startswith(prefix):
                query = cleaned[len(prefix) :].strip()
                return query if query else cleaned
        return cleaned

    def _normalize_text(self, value: Any, limit: int = 280) -> str | None:
        if value is None:
            return None
        compact = " ".join(str(value).split())
        if not compact:
            return None
        if len(compact) > limit:
            compact = compact[:limit].rstrip() + "..."
        return compact

    def _parse_sync_payload(self, objective: str) -> dict[str, Any] | None:
        match = re.match(r"^sync_turn\s*:\s*(\{.*\})\s*$", objective, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _sync_turn_state(self, payload: dict[str, Any]) -> tuple[str, list[Artifact]]:
        state = self.manager.load_state()
        if not isinstance(state, dict):
            state = {}
            self.manager.state = state

        context = state.setdefault("global_context", {})
        if not isinstance(context, dict):
            context = {}
            state["global_context"] = context

        active_focus = self._normalize_text(payload.get("active_focus"), limit=280)
        if active_focus:
            context["active_focus"] = active_focus

        active_tasks_payload = payload.get("active_tasks")
        active_tasks_text: str | None = None
        if isinstance(active_tasks_payload, list):
            cleaned: list[str] = []
            for item in active_tasks_payload:
                normalized = self._normalize_text(item, limit=180)
                if normalized:
                    cleaned.append(normalized)
            if cleaned:
                active_tasks_text = "\n".join(cleaned)
        elif isinstance(active_tasks_payload, str):
            active_tasks_text = self._normalize_text(active_tasks_payload, limit=520)
        if active_tasks_text:
            context["active_tasks"] = active_tasks_text

        next_instruction = self._normalize_text(payload.get("next_instruction"), limit=280)
        if next_instruction:
            context["next_instruction"] = next_instruction

        milestones = state.get("recent_milestones", [])
        if not isinstance(milestones, list):
            milestones = []

        milestone = self._normalize_text(payload.get("milestone"), limit=280)
        if milestone and (not milestones or milestones[-1] != milestone):
            milestones.append(milestone)

        max_milestones = payload.get("max_milestones", self.MAX_RECENT_MILESTONES)
        if not isinstance(max_milestones, int):
            max_milestones = self.MAX_RECENT_MILESTONES
        max_milestones = max(1, min(max_milestones, 64))
        state["recent_milestones"] = milestones[-max_milestones:]

        self.manager.save_state(state)

        artifacts: list[Artifact] = [Artifact(type="file", path=".memory/state.json")]

        knowledge_node = self._normalize_text(payload.get("knowledge_node"), limit=80)
        knowledge_content = self._normalize_text(payload.get("knowledge_content"), limit=2500)
        if knowledge_node and knowledge_content:
            normalized = self.manager.record_knowledge(knowledge_node, knowledge_content)
            artifacts.append(Artifact(type="file", path=f".memory/knowledge_base/{normalized}.md"))

        log_message = self._normalize_text(payload.get("log_message"), limit=400)
        if log_message:
            self.manager.log_event(log_message)

        return "Synchronized long-term memory state for completed stage.", artifacts

    async def run(self, packet: TaskPacket) -> ResultPacket:
        objective = packet.objective.strip()
        self.log(f"Processing memory objective: {objective}")

        status = "SUCCESS"
        error_log = None
        summary = ""
        artifacts: list[Artifact] = []

        try:
            lowered = objective.lower()
            if lowered.startswith("sync_turn"):
                payload = self._parse_sync_payload(objective)
                if payload is None:
                    raise ValueError("Invalid sync_turn format. Use: sync_turn: {json-payload}")
                summary, sync_artifacts = self._sync_turn_state(payload)
                artifacts.extend(sync_artifacts)

            elif lowered.startswith("store") or lowered.startswith("record"):
                parsed = self._parse_store_command(objective)
                if not parsed:
                    raise ValueError("Invalid store format. Use: store <node>: <content>")
                node, content = parsed
                normalized = self.manager.record_knowledge(node, content)
                artifacts.append(Artifact(type="file", path=f".memory/knowledge_base/{normalized}.md"))
                summary = f"Stored knowledge node '{normalized}'."

            elif lowered.startswith("retrieve") or lowered.startswith("search"):
                query = self._parse_retrieval_query(objective)
                results = self.retriever.semantic_search_simulated(query)
                if not results:
                    summary = f"No memory matches found for '{query}'."
                else:
                    node_names = ", ".join(result["node"] for result in results[:5])
                    summary = f"Found {len(results)} memory matches for '{query}': {node_names}"
                    for result in results[:5]:
                        artifacts.append(
                            Artifact(type="memory_node", path=f".memory/knowledge_base/{result['node']}.md")
                        )

            else:
                raise ValueError("Unknown memory operation. Use store/record/retrieve/search.")

        except Exception as exc:
            status = "FAILED"
            error_log = str(exc)
            summary = "Memory operation failed"

        return ResultPacket(
            task_id=packet.task_id,
            status=status,
            output_summary=summary,
            artifacts=artifacts,
            error_log=error_log,
            completed_at=datetime.now(),
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MemoryAgent with a TaskPacket payload")
    parser.add_argument("--memory-root", default=".memory", help="Path to the memory root directory")
    parser.add_argument("--packet-json", help="Inline TaskPacket JSON payload")
    parser.add_argument("--packet-file", help="Path to a TaskPacket JSON payload file")
    return parser


def _load_packet_payload(args: argparse.Namespace) -> dict[str, Any]:
    raw_payload = ""
    if args.packet_json:
        raw_payload = args.packet_json
    elif args.packet_file:
        raw_payload = Path(args.packet_file).read_text(encoding="utf-8")
    else:
        raw_payload = sys.stdin.read()

    if not raw_payload.strip():
        raise ValueError("TaskPacket payload is required via --packet-json, --packet-file, or stdin")

    decoded = json.loads(raw_payload)
    if not isinstance(decoded, dict):
        raise ValueError("TaskPacket payload must be a JSON object")
    return decoded


def _build_task_packet(payload: dict[str, Any]) -> TaskPacket:
    if hasattr(TaskPacket, "model_validate"):
        return TaskPacket.model_validate(payload)
    return TaskPacket(**payload)


def _packet_to_json(packet: ResultPacket) -> str:
    if hasattr(packet, "model_dump"):
        payload = packet.model_dump()
    elif hasattr(packet, "dict"):
        payload = packet.dict()
    else:
        payload = json.loads(packet.model_dump_json())
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        payload = _load_packet_payload(args)
        packet = _build_task_packet(payload)
        agent = MemoryAgent(memory_root=args.memory_root)
        result = asyncio.run(agent.run(packet))
        print(_packet_to_json(result))
        return 0 if result.status == "SUCCESS" else 1
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
