import os
import json
import requests
import argparse
import sys
from datetime import datetime

try:
    from scripts.memory_manager import MemoryManager
    from scripts.context_retriever import ContextRetriever
except ImportError:
    from memory_manager import MemoryManager
    from context_retriever import ContextRetriever

class LLMClient:
    """A client to interact with the configured LLM provider."""
    def __init__(self, config_path=".claw/settings.local.json"):
        self.config = self._load_config(config_path)
        self.api_key = self.config.get("env", {}).get("OPENAI_API_KEY")
        self.base_url = self.config.get("env", {}).get("OPENAI_BASE_URL")
        # Fallback for base_url if not found
        if not self.base_url:
             self.base_url = "http://127.0.0.1:1234/v1" 
        self.model = self.config.get("model", "gpt-3.5-turbo")

    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
            return {}

    def chat(self, prompt, system_prompt="You are a helpful assistant."):
        """Sends a request to the LLM API."""
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"❌ LLM Error: {str(e)}"

class AgentEngine:
    def __init__(self, memory_root=".memory", config_path=".claw/settings.local.json"):
        self.memory_manager = MemoryManager(memory_root)
        self.context_retriever = ContextRetriever(memory_root)
        self.llm = LLMClient(config_path)
        print(f"🤖 Agent Engine initialized with memory root: {memory_root}")

    def process_task(self, task_description):
        """The core reasoning loop using real LLM calls."""
        if not task_description or not task_description.strip():
            return

        print(f"\n🚀 [Task Received]: {task_description}")
        
        # 1. Planning & Retrieval Phase
        print("🔍 [Phase 1: Planning & Retrieval] Using LLM to plan and search...")
        
        extraction_prompt = (
            f"Extract the most important technical keywords or concepts from this task description. "
            f"Return only a comma-separated list of words.\n\nTask: {task_description}"
        )
        keywords_raw = self.llm.chat(extraction_prompt, system_prompt="You are an expert information extraction assistant.")
        keywords = [kw.strip() for kw in keywords_raw.split(',') if len(kw.strip()) > 1]
        print(f"  💡 LLM extracted keywords: {keywords}")

        found_context = []
        for kw in keywords:
            results = self.context_retriever.semantic_search_simulated(kw)
            if results:
                print(f"  ✅ Found relevant context for '{kw}': {len(results)} matches.")
                found_context.extend(results)
            else:
                print(f"  ⚠️ No specific knowledge found for keyword: '{kw}'")

        # 2. Reasoning Phase (Real LLM Synthesis)
        print("🧠 [Phase 2: Reasoning] Synthesizing answer with LLM...")
        
        context_str = ""
        if found_context:
            context_str = "\n".join([f"- {c.get('node', 'Unknown')}: {c.get('snippet', c.get('content', 'No content'))}" for c in found_context])
        
        reasoning_prompt = (
            f"Task: {task_description}\n\n"
            f"Relevant Knowledge from Memory:\n{context_str if context_str else 'No relevant knowledge found.'}\n\n"
            f"Please provide a comprehensive answer based on the provided knowledge. "
            f"If the knowledge is insufficient, use your internal expertise but clearly state that you are supplementing it."
        )
        
        answer = self.llm.chat(reasoning_prompt, system_prompt="You are a highly intelligent technical assistant.")
        print(f"📝 [Final Answer]:\n{answer}")

        # 3. Learning Phase (Self-Evolution)
        print("✨ [Phase 3: Learning] Analyzing for new insights to record...")
        
        learning_prompt = (
            f"Review the task and your previous answer. "
            f"Identify any specific technical rules, definitions, or summarized facts that are worth saving in a permanent knowledge base. "
            f"Return them in a JSON format: {{\"node_name\": \"content\"}}. "
            f"If there is nothing new to record, return an empty JSON object {{}}.\n\n"
            f"Task: {task_description}\n"
            f"Answer provided: {answer}"
        )

        learning_response = self.llm.chat(learning_prompt, system_prompt="You are a knowledge extraction agent.")
        
        new_insights = {}
        try:
            json_str = learning_response.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                 json_str = json_str.split("```")[1].split("```")[0].strip()
            
            new_insights = json.loads(json_str)
        except Exception as e:
            print(f"  ⚠️ Failed to parse learning insights: {e}. Response was: {learning_response}")

        if new_insights:
            print("✨ [Phase 3: Learning] New insights detected! Updating memory...")
            for insight_node, insight_content in new_insights.items():
                self.memory_manager.record_knowledge(insight_node, insight_content)
                print(f"  ✅ Learned: {insight_node}")
        else:
            print("😴 [Phase 3: Learning] No new insights to record.")

def main():
    parser = argparse.ArgumentParser(description="Agent Engine V2 - Task Processor")
    parser.add_argument("--task", type=str, help="The task description to process.")
    parser.add_argument("--config", type=str, default=".claw/settings.local.json", help="Path to config file.")
    parser.add_argument("--memory", type=str, default=".memory", help="Path to memory root.")
    
    args = parser.parse_args()
    engine = AgentEngine(memory_root=args.memory, config_path=args.config)

    if args.task:
        # Mode 1: Direct task execution via CLI
        engine.process_task(args.task)
    else:
        # Mode 2: Interactive REPL mode
        print("\n⌨️  Interactive Mode Enabled. Type 'exit' or 'quit' to stop.")
        while True:
            try:
                user_input = input("\n👤 Agent Command > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ['exit', 'quit']:
                    print("👋 Exiting Engine...")
                    break
                engine.process_task(user_input)
            except EOFError:
                break
            except Exception as e:
                print(f"❌ Error in REPL: {e}")

if __name__ == "__main__":
    main()
