import os
import json
from datetime import datetime

try:
    from scripts.memory_manager import MemoryManager
    from scripts.context_retriever import ContextRetriever
except ImportError:
    from memory_manager import MemoryManager
    from context_retriever import ContextRetriever

class AgentEngine:
    def __init__(self, memory_root=".memory"):
        self.memory_manager = MemoryManager(memory_root)
        self.context_retriever = ContextRetriever(memory_root)
        print(f"🤖 Agent Engine initialized with memory root: {memory_root}")

    def process_task(self, task_description):
        """The core reasoning loop."""
        print(f"\n🚀 [Task Received]: {task_description}")
        
        # 1. Planning & Retrieval Phase
        print("🔍 [Phase 1: Planning & Retrieval] Searching for relevant knowledge...")
        # Simple keyword extraction simulation (in real life, use an LLM)
        keywords = self._extract_keywords(task_description)
        found_context = []
        
        for kw in keywords:
            results = self.context_retriever.semantic_search_simulated(kw)
            if results:
                print(f"  ✅ Found relevant context for '{kw}': {len(results)} matches.")
                found_context.extend(results)
            else:
                print(f"  ⚠️ No specific knowledge found for keyword: '{kw}'")

        # 2. Reasoning Phase (Simulated)
        print("🧠 [Phase 2: Reasoning] Synthesizing answer based on context...")
        answer, new_insights = self._reason(task_description, found_context)
        print(f"📝 [Final Answer]:\n{answer}")

        # 3. Learning Phase (Self-Evolution)
        if new_insights:
            print("✨ [Phase 3: Learning] New insights detected! Updating memory...")
            for insight_node, insight_content in new_insights.items():
                self.memory_manager.record_knowledge(insight_node, insight_content)
                print(f"  ✅ Learned: {insight_node}")
        else:
            print("😴 [Phase 3: Learning] No new insights to record.")

    def _extract_keywords(self, text):
        """Simple keyword extraction simulation."""
        # In a real agent, this would be an LLM call.
        # Here we just split by spaces and filter short words.
        words = text.lower().replace('?', '').replace('.', '').split()
        return [w for w in words if len(w) > 3]

    def _reason(self, task, context):
        """Simulated reasoning engine."""
        # In a real agent, this is the LLM generation step.
        # Here we simulate a response and potential new knowledge discovery.
        
        if not context:
            answer = "I don't have enough information in my memory to answer this task specifically."
            new_insights = {}
        else:
            # Simulate generating an answer based on found snippets
            context_str = "\n".join([f"- {c['node']}: {c['snippet']}" for c in context])
            answer = f"Based on my existing knowledge:\n{context_str}\n\nI can conclude that the task is related to the retrieved topics."
            
            # Simulate discovering a new, specific piece of knowledge
            new_insights = {}
            if "rust" in task.lower() and "ownership" in task.lower():
                new_insight_node = "rust_ownership_summary"
                new_insight_content = "Rust ownership is characterized by three rules: 1. Each value has an owner; 2. There can only be one owner at a time; 3. When the owner goes out of scope, the value is dropped."
                new_insights[new_insight_node] = new_insight_content

        return answer, new_insights

if __name__ == "__main__":
    engine = AgentEngine()
    
    # Test Case 1: Task with existing knowledge
    print("\n--- TEST CASE 1: Existing Knowledge ---")
    engine.process_task("Tell me about Rust ownership.")

    # Test Case 2: Task without existing knowledge (forcing new learning)
    print("\n--- TEST CASE 2: New Knowledge Discovery ---")
    engine.process_task("Explain the core rules of Rust memory management.")
