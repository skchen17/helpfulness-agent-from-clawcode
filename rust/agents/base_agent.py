import json
from abc import ABC, abstractmethod
from typing import Any
from agents.protocol import TaskPacket, ResultPacket

class BaseAgent(ABC):
    """Abstract base class for all sub-agents."""
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def run(self, packet: TaskPacket) -> ResultPacket:
        """The main execution method for the agent using the communication protocol."""
        pass

    def log(self, message: str):
        print(f"[{self.name}] {message}")
