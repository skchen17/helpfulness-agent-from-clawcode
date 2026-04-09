import subprocess
from datetime import datetime
from agents.base_agent import BaseAgent
from agents.protocol import TaskPacket, ResultPacket


class ActionAgent(BaseAgent):
    """Specialist in interacting with the local environment (Shell, Filesystem)."""
    def __init__(self):
        super().__init__("ActionExpert")

    async def run(self, packet: TaskPacket) -> ResultPacket:
        command = packet.objective.strip()
        self.log(f"Executing command: {command}")

        artifacts = []
        error_log = None
        status = "SUCCESS"
        output_summary = ""

        if not command:
            return ResultPacket(
                task_id=packet.task_id,
                status="FAILED",
                output_summary="Command is empty",
                artifacts=artifacts,
                error_log="Task objective cannot be empty for ActionAgent",
                completed_at=datetime.now(),
            )

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                first_line = stdout.strip().splitlines()[0] if stdout.strip() else "(no output)"
                output_summary = (
                    f"Command executed successfully. Output length: {len(stdout)} chars. "
                    f"First line: {first_line[:120]}"
                )
            else:
                status = "FAILED"
                error_log = stderr
                output_summary = f"Command failed with return code {process.returncode}"

        except Exception as e:
            status = "FAILED"
            error_log = str(e)
            output_summary = "An exception occurred during execution"

        return ResultPacket(
            task_id=packet.task_id,
            status=status,
            output_summary=output_summary,
            artifacts=artifacts,
            error_log=error_log,
            completed_at=datetime.now()
        )
