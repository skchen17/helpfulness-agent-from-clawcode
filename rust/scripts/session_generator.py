import json
import os
from datetime import datetime
import re

class SessionGenerator:
    def __init__(self, memory_manager, state_path=".memory/state.json", 
                 spec_path=".memory/session_structure_spec.md",
                 output_dir=".memory"):
        self.mm = memory_manager
        self.state_path = state_path
        self.spec_path = spec_path
        self.output_dir = output_dir
        
    def generate(self, session_id=None):
        """Generates a new .md session template based on current state."""
        self.mm.load_state()
        state = self.mm.state
        global_context = state.get("global_context", {})
        
        # 1. Metadata Construction (YAML-like)
        timestamp = datetime.now().isoformat()
        agent_id = global_context.get("agent_identity", "Orchestrator_Agent")
        if not session_id:
            session_id = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
        metadata = [
            "---",
            f"session_id: \"{session_id}\"",
            f"timestamp: \"{timestamp}\"",
            f"agent: \"{agent_id}\"",
            f"status: \"active\"",
            "---",
            ""
        ]

        # 2. Focus & Summary (From state)
        focus = global_context.get("active_focus", "No active focus set.")
        progress_lines = []
        milestones = state.get("recent_milestones", [])
        for m in milestones:
            # Robustly clean up the milestone string using regex
            # This handles both "Session Update (date): text" and other variations
            clean_m = re.sub(r'^.*?:\s*', '', m).strip()
            progress_lines.append(f"- {clean_m}")
        
        progress_section = [
            "## 🎯 Current Focus",
            focus,
            "",
            "## ✅ Progress Summary"
        ]
        if progress_lines:
            progress_section.extend(progress_lines)
        else:
            progress_section.append("- No recent milestones recorded.")
        
        # 3. Semantic Task Queue (Parsing from state.active_tasks or global_context.active_tasks)
        task_queue_section = ["## 🚧 Active Task Queue"]
        # Check both root and global_context for tasks
        tasks_text = global_context.get("active_tasks") or state.get("active_tasks", "")
        if tasks_text:
            # Clean up potential artifacts from stringified lists
            cleaned_tasks = tasks_text.strip().strip('[]').strip("'").strip('"')
            # If it's a comma-separated list, convert to markdown bullets
            if ',' in cleaned_tasks and '\n' not in cleaned_tasks:
                task_list = [t.strip() for t in cleaned_tasks.split(',')]
                task_queue_section.extend([f"- [ ] {t}" for t in task_list])
            else:
                # If it already looks like markdown or a single block, use as is
                task_queue_section.append(tasks_text.strip())
        else:
            task_queue_section.append("- [ ] No active tasks defined.")

        # 4. Knowledge Context (From state)
        knowledge_nodes = global_context.get("key_knowledge_nodes", [])
        knowledge_section = ["## 📚 Knowledge Context"]
        if knowledge_nodes:
            for node in knowledge_nodes:
                knowledge_section.append(f"- [{node}](.memory/knowledge_base/{node}.md)")
        else:
            knowledge_section.append("- No active knowledge nodes.")

        # 5. Next Step Instruction
        next_step = global_context.get("next_instruction", "No next instruction set.")
        next_step_section = [
            "",
            "## 🚀 Next Step Instruction",
            next_step
        ]

        # Combine everything
        full_content = "\n".join(metadata + progress_section + task_queue_section + knowledge_section + next_step_section)
        
        output_path = os.path.join(self.output_dir, "session_template.md")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
            
        print(f"✅ New session template generated at: {output_path}")
        return output_path

if __name__ == "__main__":
    import sys
    try:
        from scripts.memory_manager import MemoryManager
    except ImportError:
        from memory_manager import MemoryManager
    
    mm = MemoryManager()
    generator = SessionGenerator(mm)
    
    if len(sys.argv) < 2:
        print("Usage: python session_generator.py [generate]")
        sys.exit(1)
        
    cmd = sys.argv[1]
    if cmd == "generate":
        generator.generate()
    else:
        print(f"Unknown command: {cmd}")

