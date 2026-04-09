import json
import os

state_path = ".memory/state.json"

if not os.path.exists(state_path):
    print(f"Error: {state_path} not found.")
    exit(1)

with open(state_path, 'r') as f:
    data = json.load(f)

# 1. Remove the erroneous "--content" key if it exists
if "--content" in data:
    print("Removing erroneous '--content' key...")
    del data["--content"]

# 2. Define the new content we want to inject
new_focus = "System Architecture established; preparing for 'Declarative Initialization' validation and Orchestrator refactoring."
new_milestone = "Session Update (2026-03-31): Successfully completed system architecture mapping and verified declarative initialization prototype."

# 3. Update the correct fields
print(f"Updating active_focus to: {new_focus}")
data["global_context"]["active_focus"] = new_focus

print(f"Updating recent_milestones...")
data["recent_milestones"] = [new_milestone]

# 4. Update the timestamp and other metadata if necessary
from datetime import datetime
data["last_updated"] = datetime.now().isoformat()

# Write back to file
with open(state_path, 'w') as f:
    json.dump(data, f, indent=4)

print("Successfully repaired state.json!")
