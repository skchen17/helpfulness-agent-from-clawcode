import os
import json
import subprocess
from memory_manager import MemoryManager

def test_memory_system():
    print("🚀 Starting Memory System Verification...\n")
    manager = MemoryManager()
    
    # 1. Test Update State
    print("--- Testing: update_state_field ---")
    test_task = "Verify memory manager"
    try:
        # Using the CLI interface via subprocess to simulate real-world usage
        subprocess.run(["python3", "scripts/memory_manager.py", "update", "active_tasks", test_task], check=True)
        
        state = manager.load_state()
        if state.get("active_tasks") == test_task:
            print("✅ SUCCESS: State field updated correctly.")
        else:
            print(f"❌ FAILURE: Expected '{test_task}', got '{state.get('active_tasks')}'")
    except Exception as e:
        print(f"❌ ERROR during update test: {e}")

    # 2. Test Record Knowledge
    print("\n--- Testing: record_knowledge ---")
    node_name = "test_node"
    content = "# This is a test knowledge node\nContent for testing."
    try:
        subprocess.run(["python3", "scripts/memory_manager.py", "record", node_name, content], check=True)
        
        # Check file existence
        kb_file = os.path.join(".memory/knowledge_base", f"{node_name}.md")
        if os.path.exists(kb_file):
            print("✅ SUCCESS: Knowledge node file created.")
            with open(kb_file, 'r') as f:
                if f.read() == content:
                    print("✅ SUCCESS: Content integrity verified.")
                else:
                    print("❌ FAILURE: Content mismatch.")
        else:
            print("❌ FAILURE: Knowledge node file not found.")

        # Check state index update
        state = manager.load_state()
        nodes = state.get("global_context", {}).get("key_knowledge_nodes", [])
        if node_name in nodes:
            print(f"✅ SUCCESS: '{node_name}' added to global context index.")
        else:
            print(f"❌ FAILURE: '{node_name}' not found in state index.")

    except Exception as e:
        print(f"❌ ERROR during record test: {e}")

    # 3. Test Logging
    print("\n--- Testing: log_event ---")
    log_msg = "Testing log event functionality"
    try:
        subprocess.run(["python3", "scripts/memory_manager.py", "log", log_msg], check=True)
        
        log_path = ".memory/logs/evolution.log"
        with open(log_path, 'r') as f:
            logs = f.read()
            if log_msg in logs:
                print("✅ SUCCESS: Event found in evolution.log.")
            else:
                print(f"❌ FAILURE: Log message not found in {log_path}")
    except Exception as e:
        print(f"❌ ERROR during log test: {e}")

    print("\n🏁 Verification Complete.")

if __name__ == "__main__":
    test_memory_system()
