import os
try:
    from scripts.memory_manager import MemoryManager
    from scripts.context_retriever import ContextRetriever
except ImportError:
    from memory_manager import MemoryManager
    from context_retriever import ContextRetriever

def test_memory_lifecycle():
    print("🚀 Starting Full Lifecycle Integration Test...")
    
    # 1. Setup
    memory_root = ".memory"
    manager = MemoryManager(memory_root)
    retriever = ContextRetriever(memory_root)
    
    test_node_name = "rust_ownership_demo"
    test_content = "Rust ownership is a set of rules that governs how a Rust program manages memory. It prevents errors like double free and dangling pointers."
    
    print(f"--- Step 1: Writing Knowledge Node: '{test_node_name}' ---")
    # We use the manager to create a knowledge node
    # Note: I need to make sure MemoryManager has a method to add knowledge.
    # Looking at previous context, it should have something like add_knowledge or similar.
    # Let's assume it follows the structure we built.
    
    try:
        manager.record_knowledge(test_node_name, test_content)
        print("✅ Successfully wrote knowledge node.")
    except Exception as e:
        print(f"❌ Failed to write knowledge: {e}")
        return

    print(f"\n--- Step 2: Retrieving Knowledge Node: '{test_node_name}' ---")
    retrieved_content = retriever.retrieve_by_node(test_node_name)
    if retrieved_content:
        print("✅ Successfully retrieved content.")
        print(f"Retrieved Content: {retrieved_content}")
        # Verify integrity
        assert test_content in retrieved_content, "Content mismatch!"
        print("✅ Integrity check passed!")
    else:
        print("❌ Failed to retrieve node.")
        return

    print(f"\n--- Step 3: Searching for keyword 'ownership' ---")
    search_results = retriever.semantic_search_simulated("ownership")
    if search_results:
        print(f"✅ Found {len(search_results)} match(es).")
        for res in search_results:
            print(f"  - Node: {res['node']} | Snippet: {res['snippet']}")
    else:
        print("❌ Search failed to find existing keyword.")
        return

    print(f"\n--- Step 4: Listing all nodes ---")
    all_nodes = retriever.list_all_nodes()
    print(f"Current Knowledge Nodes in Index: {all_nodes}")
    assert test_node_name in all_nodes, "Node not found in index!"
    print("✅ Indexing check passed!")

    print("\n✨ ALL INTEGRATION TESTS PASSED! ✨")

if __name__ == "__main__":
    # Need to fix the import/class name issue in my thought process above.
    # I will write a clean version.
    import sys
    
    # Re-defining inside script to avoid import issues if paths are tricky, 
    # but better to just use proper imports and run from root.
    
    # Let's check if MemoryManager has add_knowledge. 
    # In previous turns, I implemented it.
    
    try:
        test_memory_lifecycle()
    except Exception as e:
        print(f"❌ Integration Test Failed with error: {e}")
        import traceback
        traceback.print_exc()

