from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from scripts.memory_manager import MemoryManager
except ImportError:
    from memory_manager import MemoryManager


class ContextRetriever:
    def __init__(self, memory_root: str = ".memory"):
        self.memory_root = Path(memory_root)
        self.kb_dir = self.memory_root / "knowledge_base"
        self.manager = MemoryManager(memory_root)

    def retrieve_by_node(self, node_name: str) -> str | None:
        file_path = self.kb_dir / f"{node_name}.md"
        if not file_path.exists():
            return None
        return file_path.read_text(encoding="utf-8")

    def list_all_nodes(self) -> list[str]:
        state = self.manager.load_state()
        nodes = state.get("global_context", {}).get("key_knowledge_nodes", [])
        return nodes if isinstance(nodes, list) else []

    def semantic_search_simulated(
        self,
        query_keyword: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        needle = query_keyword.strip().lower()
        if not needle:
            return []

        results: list[dict[str, Any]] = []
        for node in self.list_all_nodes():
            content = self.retrieve_by_node(node)
            if not content:
                continue

            content_lower = content.lower()
            if needle not in node.lower() and needle not in content_lower:
                continue

            index = content_lower.find(needle)
            if index == -1:
                snippet = " ".join(content.split())[:160]
            else:
                start = max(0, index - 80)
                end = min(len(content), index + len(needle) + 80)
                snippet = " ".join(content[start:end].split())

            results.append(
                {
                    "node": node,
                    "snippet": snippet + ("..." if len(snippet) < len(content) else ""),
                }
            )
            if len(results) >= max_results:
                break

        return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Knowledge retrieval helper")
    parser.add_argument("command", choices=["list", "get", "search"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--memory", default=".memory")
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args(argv)

    retriever = ContextRetriever(memory_root=args.memory)

    if args.command == "list":
        for node in retriever.list_all_nodes():
            print(node)
        return 0

    if args.command == "get":
        if not args.value:
            raise ValueError("get requires a node name")
        content = retriever.retrieve_by_node(args.value)
        if content is None:
            print("Node not found")
            return 1
        print(content)
        return 0

    if not args.value:
        raise ValueError("search requires a query")
    for result in retriever.semantic_search_simulated(
        args.value,
        max_results=args.max_results,
    ):
        print(f"{result['node']}: {result['snippet']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
