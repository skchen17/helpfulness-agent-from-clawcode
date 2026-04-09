from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_STATE: dict[str, Any] = {
    "global_context": {
        "key_knowledge_nodes": [],
        "active_focus": None,
        "active_skills": [],
        "active_tasks": "",
        "next_instruction": "",
    },
    "recent_milestones": [],
}

MAX_STATE_ARCHIVES = 80
MAX_NODE_ARCHIVES = 30


class MemoryManager:
    def __init__(self, memory_root: str = ".memory"):
        self.memory_root = Path(memory_root)
        self.state_path = self.memory_root / "state.json"
        self.kb_dir = self.memory_root / "knowledge_base"
        self.log_dir = self.memory_root / "logs"
        self.archive_dir = self.memory_root / "archive"
        self.state_archive_dir = self.archive_dir / "state"
        self.knowledge_archive_dir = self.archive_dir / "knowledge"
        self.log_path = self.log_dir / "evolution.log"
        self.state: dict[str, Any] = {}
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        self.kb_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.state_archive_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_archive_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self.state = deepcopy(DEFAULT_STATE)
            self.save_state()

    def _timestamp_token(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    def _content_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]

    def _latest_archive(self, archive_root: Path, node_prefix: str, suffix: str) -> Path | None:
        candidates = sorted(
            archive_root.glob(f"{node_prefix}_*{suffix}"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None

    def _trim_archives(self, archive_root: Path, node_prefix: str, suffix: str, keep: int) -> None:
        if keep <= 0:
            return

        candidates = sorted(
            archive_root.glob(f"{node_prefix}_*{suffix}"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale in candidates[keep:]:
            try:
                stale.unlink()
            except FileNotFoundError:
                continue

    def _archive_content(
        self,
        archive_root: Path,
        node_prefix: str,
        content: str,
        suffix: str,
        keep: int,
    ) -> Path | None:
        archive_root.mkdir(parents=True, exist_ok=True)
        digest = self._content_hash(content)
        latest = self._latest_archive(archive_root, node_prefix, suffix)
        if latest is not None and latest.stem.endswith(digest):
            return None

        token = self._timestamp_token()
        snapshot = archive_root / f"{node_prefix}_{token}_{digest}{suffix}"
        snapshot.write_text(content, encoding="utf-8")
        self._trim_archives(archive_root, node_prefix, suffix, keep)
        return snapshot

    def _archive_state_snapshot(self) -> None:
        if not self.state:
            return
        serialized = json.dumps(self.state, indent=2, ensure_ascii=False)
        self._archive_content(
            archive_root=self.state_archive_dir,
            node_prefix="state",
            content=serialized,
            suffix=".json",
            keep=MAX_STATE_ARCHIVES,
        )

    def _archive_knowledge_snapshot(self, normalized_node: str, content: str) -> None:
        self._archive_content(
            archive_root=self.knowledge_archive_dir,
            node_prefix=normalized_node,
            content=content,
            suffix=".md",
            keep=MAX_NODE_ARCHIVES,
        )

    def _ensure_state_shape(self, state: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(DEFAULT_STATE)
        global_context = merged["global_context"]

        existing_global = state.get("global_context", {})
        if isinstance(existing_global, dict):
            global_context.update(existing_global)

        for key, value in state.items():
            if key != "global_context":
                merged[key] = value

        return merged

    def load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            self.state = deepcopy(DEFAULT_STATE)
            self.save_state()
            return self.state

        with self.state_path.open("r", encoding="utf-8") as handle:
            parsed = json.load(handle)

        if not isinstance(parsed, dict):
            raise ValueError(f"State file must be a JSON object: {self.state_path}")

        self.state = self._ensure_state_shape(parsed)
        return self.state

    def save_state(self, state: dict[str, Any] | None = None) -> None:
        if state is not None:
            self.state = self._ensure_state_shape(state)
        elif not self.state:
            self.state = deepcopy(DEFAULT_STATE)

        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(self.state, handle, indent=2, ensure_ascii=False)

        # Persist a deduplicated snapshot so history can be audited or recovered.
        self._archive_state_snapshot()

    def get_all_state(self) -> dict[str, Any]:
        return self.load_state()

    def update_state_field(self, path: str, value: Any) -> None:
        if not path.strip():
            raise ValueError("state path cannot be empty")

        self.load_state()
        keys = [part.strip() for part in path.split(".") if part.strip()]
        if not keys:
            raise ValueError("state path cannot be empty")

        target: dict[str, Any] = self.state
        for key in keys[:-1]:
            branch = target.get(key)
            if not isinstance(branch, dict):
                branch = {}
                target[key] = branch
            target = branch

        target[keys[-1]] = value
        self.save_state()

    def _extract_markdown_section(self, content: str, title_hint: str) -> str | None:
        pattern = rf"^##\s+.*{re.escape(title_hint)}.*\n(.*?)(?=^##\s+|\Z)"
        match = re.search(pattern, content, flags=re.MULTILINE | re.DOTALL)
        if not match:
            return None
        value = match.group(1).strip()
        return value or None

    def initialize_from_markdown(self, md_path: str) -> bool:
        markdown_path = Path(md_path)
        if not markdown_path.exists():
            raise FileNotFoundError(f"Session file not found at {markdown_path}")

        content = markdown_path.read_text(encoding="utf-8")
        self.load_state()

        focus = self._extract_markdown_section(content, "Current Focus")
        if focus:
            self.update_state_field("global_context.active_focus", focus)

        progress = self._extract_markdown_section(content, "Progress Summary")
        if progress:
            summary = " ".join(progress.split())
            summary = summary[:120]
            marker = datetime.now().strftime("%Y-%m-%d")
            entry = f"Session Update ({marker}): {summary}"
            milestones = self.state.get("recent_milestones", [])
            if entry not in milestones:
                milestones.append(entry)
                self.state["recent_milestones"] = milestones[-5:]
                self.save_state()

        tasks = self._extract_markdown_section(content, "Active Task Queue")
        if tasks:
            self.update_state_field("global_context.active_tasks", tasks)

        next_step = self._extract_markdown_section(content, "Next Step Instruction")
        if next_step:
            self.update_state_field("global_context.next_instruction", next_step)

        self.log_event(f"Initialized state from markdown: {markdown_path}")
        return True

    def _normalize_node_name(self, node_name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", node_name.strip())
        cleaned = cleaned.strip("_")
        if not cleaned:
            raise ValueError("node name cannot be empty")
        return cleaned

    def record_knowledge(self, node_name: str, content: str, is_skill: bool = False) -> str:
        normalized = self._normalize_node_name(node_name)
        file_path = self.kb_dir / f"{normalized}.md"
        file_path.write_text(content, encoding="utf-8")
        self._archive_knowledge_snapshot(normalized, content)

        self.load_state()
        context = self.state.setdefault("global_context", {})

        if is_skill:
            skills = context.setdefault("active_skills", [])
            if normalized not in skills:
                skills.append(normalized)
        else:
            nodes = context.setdefault("key_knowledge_nodes", [])
            if normalized not in nodes:
                nodes.append(normalized)

        self.save_state()
        kind = "skill" if is_skill else "knowledge node"
        self.log_event(f"Added {kind}: {normalized}")
        return normalized

    def get_startup_context(self) -> str:
        self.load_state()
        context = self.state.get("global_context", {})
        milestones = self.state.get("recent_milestones", [])

        parts: list[str] = []

        focus = context.get("active_focus")
        if focus:
            parts.append(f"### CURRENT FOCUS\n{focus}")

        if milestones:
            parts.append("### RECENT PROGRESS\n- " + "\n- ".join(milestones[-5:]))

        skills = context.get("active_skills", [])
        if skills:
            skill_lines: list[str] = []
            for skill_name in skills:
                skill_file = self.kb_dir / f"{skill_name}.md"
                if not skill_file.exists():
                    continue
                content = skill_file.read_text(encoding="utf-8").strip()
                if content:
                    skill_lines.append(f"- {skill_name}: {content[:200]}")
            if skill_lines:
                parts.append("### ACTIVE SKILLS\n" + "\n".join(skill_lines))

        return "\n\n".join(parts) if parts else "No active context available."

    def get_recent_logs(self, limit: int = 10) -> list[str]:
        if limit <= 0 or not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        return lines[-limit:]

    def search_knowledge(self, query: str, limit: int = 10) -> str:
        self.load_state()
        needle = query.lower().strip()
        if not needle:
            return "No matching knowledge found."

        matches: list[str] = []
        nodes = self.state.get("global_context", {}).get("key_knowledge_nodes", [])

        for node in nodes:
            file_path = self.kb_dir / f"{node}.md"
            if not file_path.exists():
                continue
            content = file_path.read_text(encoding="utf-8")
            if needle in node.lower() or needle in content.lower():
                snippet = " ".join(content.split())[:2500]
                matches.append(f"Node: {node}\nContent: {snippet}...")
                if len(matches) >= limit:
                    break

        return "\n\n".join(matches) if matches else "No matching knowledge found."

    def log_event(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] {message}\n"
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(entry)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Memory manager utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("show", help="Print full state JSON")

    update_parser = subparsers.add_parser("update", help="Update a state field")
    update_parser.add_argument("path", help="Dot path, e.g. global_context.active_focus")
    update_parser.add_argument("value", help="New value")
    update_parser.add_argument(
        "--json",
        action="store_true",
        help="Parse value as JSON before writing",
    )

    record_parser = subparsers.add_parser("record", help="Record a knowledge node")
    record_parser.add_argument("node", help="Node name")
    record_parser.add_argument("content", help="Markdown content")
    record_parser.add_argument("--skill", action="store_true", help="Record as a skill node")

    log_parser = subparsers.add_parser("log", help="Append a log entry")
    log_parser.add_argument("message", help="Message to append")

    startup_parser = subparsers.add_parser("startup", help="Print startup context")
    startup_parser.add_argument("--raw", action="store_true", help="Print without heading")

    search_parser = subparsers.add_parser("search", help="Search knowledge base")
    search_parser.add_argument("query", help="Search keyword")
    search_parser.add_argument("--limit", type=int, default=10)

    init_parser = subparsers.add_parser("init-md", help="Initialize from markdown file")
    init_parser.add_argument("path", help="Path to session markdown")

    logs_parser = subparsers.add_parser("recent-logs", help="Print recent log entries")
    logs_parser.add_argument("--limit", type=int, default=10)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    manager = MemoryManager()

    if args.command == "show":
        print(json.dumps(manager.get_all_state(), indent=2, ensure_ascii=False))
        return 0

    if args.command == "update":
        value: Any = args.value
        if args.json:
            value = json.loads(args.value)
        manager.update_state_field(args.path, value)
        print(f"Updated {args.path}")
        return 0

    if args.command == "record":
        node = manager.record_knowledge(args.node, args.content, is_skill=args.skill)
        print(f"Recorded {node}")
        return 0

    if args.command == "log":
        manager.log_event(args.message)
        print("Logged event")
        return 0

    if args.command == "startup":
        context = manager.get_startup_context()
        if args.raw:
            print(context)
        else:
            print("Startup context:")
            print(context)
        return 0

    if args.command == "search":
        print(manager.search_knowledge(args.query, limit=args.limit))
        return 0

    if args.command == "init-md":
        manager.initialize_from_markdown(args.path)
        print("Initialized from markdown")
        return 0

    if args.command == "recent-logs":
        for line in manager.get_recent_logs(limit=args.limit):
            print(line)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
