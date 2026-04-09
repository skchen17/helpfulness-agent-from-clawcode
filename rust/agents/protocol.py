from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

try:
    from pydantic import BaseModel, Field
except ImportError:
    BaseModel = None
    Field = None


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return str(value)


if BaseModel is not None:

    class ContextSnapshot(BaseModel):
        """A minimized snapshot of the environment and relevant knowledge."""

        relevant_knowledge_ids: List[str] = Field(
            default_factory=list,
            description="IDs of related knowledge nodes",
        )
        environment_vars: Dict[str, str] = Field(default_factory=dict)
        input_files: List[str] = Field(default_factory=list)


    class TaskPacket(BaseModel):
        """The payload sent from Commander to Worker (as defined in ACP)."""

        task_id: UUID = Field(default_factory=uuid4)
        parent_focus: str = Field(..., description="The current active focus of the Commander")
        objective: str = Field(..., description="Clear, single-sentence goal for this worker")
        context_snapshot: ContextSnapshot = Field(
            ...,
            description="Minimized context for the worker",
        )
        constraints: List[str] = Field(default_factory=list)
        success_criteria: Dict[str, str] = Field(
            ...,
            description="Criteria to verify task success",
        )
        created_at: datetime = Field(default_factory=datetime.now)


    class Artifact(BaseModel):
        """A piece of data or file produced by a task."""

        type: str
        path: str


    class ResultPacket(BaseModel):
        """The payload sent from Worker back to Commander (as defined in ACP)."""

        task_id: UUID
        status: str = Field(..., pattern="^(SUCCESS|FAILED|ABORTED)$")
        output_summary: str = Field(..., description="A high-level summary of what was done")
        artifacts: List[Artifact] = Field(default_factory=list)
        error_log: Optional[str] = None
        learned_insight: Optional[str] = Field(
            None,
            description="New knowledge to be promoted to global context",
        )
        completed_at: datetime = Field(default_factory=datetime.now)

else:

    @dataclass
    class ContextSnapshot:
        """A minimized snapshot of the environment and relevant knowledge."""

        relevant_knowledge_ids: List[str] = field(default_factory=list)
        environment_vars: Dict[str, str] = field(default_factory=dict)
        input_files: List[str] = field(default_factory=list)


    @dataclass
    class TaskPacket:
        """The payload sent from Commander to Worker (as defined in ACP)."""

        parent_focus: str = ""
        objective: str = ""
        context_snapshot: ContextSnapshot | Dict[str, Any] = field(default_factory=ContextSnapshot)
        success_criteria: Dict[str, str] = field(default_factory=dict)
        task_id: UUID = field(default_factory=uuid4)
        constraints: List[str] = field(default_factory=list)
        created_at: datetime = field(default_factory=datetime.now)

        def __post_init__(self) -> None:
            if isinstance(self.context_snapshot, dict):
                self.context_snapshot = ContextSnapshot(**self.context_snapshot)

        def model_dump(self) -> Dict[str, Any]:
            return asdict(self)

        def model_dump_json(self, indent: int | None = None, ensure_ascii: bool = True) -> str:
            return json.dumps(
                self.model_dump(),
                indent=indent,
                ensure_ascii=ensure_ascii,
                default=_json_default,
            )


    @dataclass
    class Artifact:
        """A piece of data or file produced by a task."""

        type: str
        path: str


    @dataclass
    class ResultPacket:
        """The payload sent from Worker back to Commander (as defined in ACP)."""

        task_id: UUID
        status: str
        output_summary: str
        artifacts: List[Artifact] = field(default_factory=list)
        error_log: Optional[str] = None
        learned_insight: Optional[str] = None
        completed_at: datetime = field(default_factory=datetime.now)

        def model_dump(self) -> Dict[str, Any]:
            return asdict(self)

        def model_dump_json(self, indent: int | None = None, ensure_ascii: bool = True) -> str:
            return json.dumps(
                self.model_dump(),
                indent=indent,
                ensure_ascii=ensure_ascii,
                default=_json_default,
            )
