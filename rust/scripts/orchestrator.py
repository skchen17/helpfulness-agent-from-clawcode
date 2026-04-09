from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

RUST_ROOT = Path(__file__).resolve().parents[1]
if str(RUST_ROOT) not in sys.path:
    sys.path.insert(0, str(RUST_ROOT))

from agents.action_agent import ActionAgent
from agents.base_agent import BaseAgent
from agents.memory_agent import MemoryAgent
from agents.protocol import ResultPacket, TaskPacket


class ReasoningAgent(BaseAgent):
    """Simple reasoning worker used to aggregate previous outputs."""

    def __init__(self, config_path: str = ".claw/settings.local.json"):
        super().__init__("ReasoningExpert")
        self._llm = None
        try:
            from scripts.agent_engine_v2 import LLMClient
        except ImportError:
            try:
                from agent_engine_v2 import LLMClient
            except ImportError:
                LLMClient = None
        if LLMClient is not None:
            self._llm = LLMClient(config_path)

    async def run(self, packet: TaskPacket) -> ResultPacket:
        objective = packet.objective.strip()
        try:
            if self._llm is not None:
                answer = self._llm.chat(
                    objective,
                    system_prompt="You are a concise technical summarizer.",
                )
                if isinstance(answer, str) and answer.strip().startswith("❌ LLM Error"):
                    answer = (
                        "LLM endpoint unavailable; fallback summary generated locally: "
                        + objective[:400]
                    )
            else:
                answer = objective[:400]
            return ResultPacket(
                task_id=packet.task_id,
                status="SUCCESS",
                output_summary=answer,
                artifacts=[],
                error_log=None,
                completed_at=datetime.now(),
            )
        except Exception as exc:
            return ResultPacket(
                task_id=packet.task_id,
                status="FAILED",
                output_summary="Reasoning failed",
                artifacts=[],
                error_log=str(exc),
                completed_at=datetime.now(),
            )


class Orchestrator(BaseAgent):
    """Master worker that plans and dispatches packetized subtasks."""

    def __init__(self, config_path: str = ".claw/settings.local.json", memory_root: str = ".memory"):
        super().__init__("MasterOrchestrator")
        self.agents = {
            "memory": MemoryAgent(memory_root),
            "action": ActionAgent(),
            "reasoning": ReasoningAgent(config_path),
        }

    def _generate_plan(self, objective: str) -> list[dict[str, str]]:
        lowered = objective.lower()
        plan: list[dict[str, str]] = []

        if "store" in lowered or "record" in lowered:
            plan.append({"agent": "memory", "task": objective})
            plan.append({"agent": "reasoning", "task": "Summarize what was stored."})
            return plan

        if "retrieve" in lowered or "search" in lowered or "tell me about" in lowered:
            keyword = objective.split("about", 1)[-1].strip() if "about" in lowered else objective
            plan.append({"agent": "memory", "task": f"retrieve {keyword}"})
            plan.append({"agent": "reasoning", "task": f"Summarize findings for: {keyword}"})
            return plan

        if "check" in lowered or "list" in lowered or "ls" in lowered:
            plan.append({"agent": "action", "task": "ls -la"})
            plan.append({"agent": "reasoning", "task": "Summarize filesystem findings."})
            return plan

        plan.append({"agent": "reasoning", "task": objective})
        return plan

    def _child_packet(self, parent: TaskPacket, objective: str) -> TaskPacket:
        return TaskPacket(
            parent_focus=parent.parent_focus,
            objective=objective,
            context_snapshot=parent.context_snapshot,
            constraints=parent.constraints,
            success_criteria=parent.success_criteria,
        )

    async def run(self, packet: TaskPacket) -> ResultPacket:
        self.log(f"Received mission: {packet.objective}")
        plan = self._generate_plan(packet.objective)
        execution_results: list[dict[str, str]] = []

        for step in plan:
            agent_name = step["agent"]
            if agent_name not in self.agents:
                return ResultPacket(
                    task_id=packet.task_id,
                    status="FAILED",
                    output_summary="Orchestration failed",
                    artifacts=[],
                    error_log=f"Unknown agent: {agent_name}",
                    completed_at=datetime.now(),
                )

            child = self._child_packet(packet, step["task"])
            result = await self.agents[agent_name].run(child)
            execution_results.append(
                {
                    "agent": agent_name,
                    "status": result.status,
                    "summary": result.output_summary,
                }
            )
            if result.status != "SUCCESS":
                return ResultPacket(
                    task_id=packet.task_id,
                    status="FAILED",
                    output_summary="Execution failed",
                    artifacts=result.artifacts,
                    error_log=result.error_log or f"Step failed in {agent_name}",
                    completed_at=datetime.now(),
                )

        report_prompt = (
            "Summarize these execution results in 2-4 concise sentences:\n"
            + json.dumps(execution_results, ensure_ascii=False)
        )
        reasoning_result = await self.agents["reasoning"].run(self._child_packet(packet, report_prompt))
        if reasoning_result.status != "SUCCESS":
            return ResultPacket(
                task_id=packet.task_id,
                status="FAILED",
                output_summary="Execution finished but summary failed",
                artifacts=[],
                error_log=reasoning_result.error_log,
                completed_at=datetime.now(),
            )

        return ResultPacket(
            task_id=packet.task_id,
            status="SUCCESS",
            output_summary=reasoning_result.output_summary,
            artifacts=[],
            error_log=None,
            learned_insight=json.dumps(execution_results, ensure_ascii=False),
            completed_at=datetime.now(),
        )


def _new_task_packet(objective: str) -> TaskPacket:
    trimmed = objective.strip()
    if not trimmed:
        raise ValueError("objective cannot be empty")
    return TaskPacket(
        parent_focus="rust-core-orchestrate",
        objective=trimmed,
        context_snapshot={
            "relevant_knowledge_ids": [],
            "environment_vars": {},
            "input_files": [str(Path.cwd())],
        },
        constraints=[],
        success_criteria={"summary": "Return a concise and actionable result."},
    )


def _task_packet_from_cli(packet_json: str | None, objective: str | None) -> TaskPacket:
    if packet_json is not None:
        payload = json.loads(packet_json)
        if not isinstance(payload, dict):
            raise ValueError("--packet-json must decode to a JSON object")
        return TaskPacket(**payload)
    if objective is not None:
        return _new_task_packet(objective)
    raise ValueError("provide --packet-json or --objective")


def _result_to_json(result: ResultPacket) -> str:
    payload = result.model_dump() if hasattr(result, "model_dump") else result.__dict__
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


async def _run_cli(
    packet_json: str | None,
    objective: str | None,
    config_path: str,
    memory_root: str,
) -> int:
    packet = _task_packet_from_cli(packet_json, objective)
    orchestrator = Orchestrator(config_path=config_path, memory_root=memory_root)
    try:
        result = await orchestrator.run(packet)
    except Exception as exc:
        task_id = getattr(packet, "task_id", uuid4())
        result = ResultPacket(
            task_id=task_id,
            status="FAILED",
            output_summary="Orchestration runtime failure",
            artifacts=[],
            error_log=str(exc),
            completed_at=datetime.now(),
        )
    print(_result_to_json(result))
    return 0 if result.status == "SUCCESS" else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the multi-agent orchestrator")
    parser.add_argument("--packet-json", help="Raw TaskPacket JSON payload")
    parser.add_argument("--objective", help="Plain objective text to wrap in a TaskPacket")
    parser.add_argument("--config-path", default=".claw/settings.local.json")
    parser.add_argument("--memory-root", default=".memory")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.packet_json is None and args.objective is None:
        orchestrator = Orchestrator(config_path=args.config_path, memory_root=args.memory_root)

        async def _demo() -> int:
            packet = TaskPacket(
                parent_focus="demo",
                objective="Tell me about Rust ownership",
                context_snapshot={
                    "relevant_knowledge_ids": [],
                    "environment_vars": {},
                    "input_files": [],
                },
                success_criteria={"summary": "A useful short answer"},
            )
            result = await orchestrator.run(packet)
            print(_result_to_json(result))
            return 0 if result.status == "SUCCESS" else 1

        raise SystemExit(asyncio.run(_demo()))

    raise SystemExit(
        asyncio.run(
            _run_cli(
                packet_json=args.packet_json,
                objective=args.objective,
                config_path=args.config_path,
                memory_root=args.memory_root,
            )
        )
    )
