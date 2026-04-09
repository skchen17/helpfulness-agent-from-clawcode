import sys
import subprocess
from datetime import datetime


class CodeExecutor:
    """
    A simple skill implementation that executes Python code or Shell commands.
    It takes an objective and attempts to find executable instructions within it.
    """
    def __init__(self, memory_manager=None):
        self.mm = memory_manager
        self.log_prefix = "[CodeExecutor]"

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{self.log_prefix} [{timestamp}] {message}")
        if self.mm:
            self.mm.log_event(f"Skill Execution: {message}")

    def execute(self, objective):
        """
        Main entry point for the skill. 
        In a real scenario, this would parse a more complex TaskPacket.
        For now, we look for 'run: <command>' pattern in the objective string.
        """
        self.log(f"Starting execution for objective: {objective}")
        
        # Simple parsing logic
        marker = "run:"
        lower = objective.lower()
        if marker in lower:
            # Keep original casing and spacing in the command payload.
            start = lower.index(marker) + len(marker)
            cmd_part = objective[start:].strip()
            return self._run_command(cmd_part)
        else:
            self.log("No executable command found in objective (no 'run:' prefix).")
            return False

    def _run_command(self, command):
        """Executes a shell command and captures output."""
        self.log(f"Executing command: {command}")
        try:
            # Use shell=True carefully - in a real agent, we'd want more control
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                self.log("Command completed successfully.")
                if result.stdout:
                    print(f"--- STDOUT ---\n{result.stdout.strip()}\n--------------")
                return True
            else:
                self.log(f"Command failed with return code {result.returncode}")
                if result.stderr:
                    print(f"--- STDERR ---\n{result.stderr.strip()}\n--------------")
                return False
        except subprocess.TimeoutExpired:
            self.log("Command timed out.")
            return False
        except Exception as e:
            self.log(f"An error occurred during execution: {e}")
            return False

if __name__ == "__main__":
    # Simple CLI test interface
    import argparse
    parser = argparse.ArgumentParser(description="Test CodeExecutor Skill")
    parser.add_argument("--objective", type=str, required=True, help="The task objective string")
    args = parser.parse_args()

    executor = CodeExecutor()
    success = executor.execute(args.objective)
    sys.exit(0 if success else 1)
