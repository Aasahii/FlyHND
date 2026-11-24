import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AgentMessage:

    performative: str  
    sender: str
    receiver: str
    action: str
    payload: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "assigned"  
    correlation_id: str = field(default_factory=lambda: f"corr-{uuid.uuid4().hex[:8]}")
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:6]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(**data)

    def format_trace(self) -> str:
        tag = f"[{self.performative.upper()}]"
        routing = f"{self.sender} -> {self.receiver}"
        action_str = f"action='{self.action}'"
        status_str = f"status={self.status}"
        return f"{tag:<10} {routing:<35} | {action_str:<32} | {status_str}"
