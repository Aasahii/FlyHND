import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from models.message import AgentMessage
from models.flight import FlightOffer
from models.memory_models import SearchRequest, TaskRecord, ConflictArbitrationRecord
from memory.tfidf_retriever import RetrievedEvidence


class WorkingMemory:

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or f"corr-{uuid.uuid4().hex[:8]}"
        self.search_request: Optional[SearchRequest] = None
        self.tasks: Dict[str, TaskRecord] = {}
        self.messages: List[AgentMessage] = []
        self.raw_offers: List[FlightOffer] = []
        self.arbitrated_offers: List[FlightOffer] = []
        self.ranked_offers: List[FlightOffer] = []
        self.conflict_records: List[ConflictArbitrationRecord] = []
        self.retrieved_evidence: List[RetrievedEvidence] = []
        self.trace_logs: List[Dict[str, Any]] = []
        self.created_at: str = datetime.now(timezone.utc).isoformat()

    def set_request(self, request: SearchRequest) -> None:
        self.search_request = request
        self.log_trace(
            agent="RequestCoordinator",
            action="init_request",
            details=f"Route: {request.origin} → {request.destination} | Date: {request.departure_date}"
        )

    def register_task(self, task_id: str, owner: str, action: str) -> None:
        self.tasks[task_id] = TaskRecord(
            task_id=task_id,
            owner=owner,
            action=action,
            status="assigned",
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def update_task_status(self, task_id: str, status: str, summary: Optional[str] = None) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            if summary:
                self.tasks[task_id].result_summary = summary

    def add_message(self, message: AgentMessage) -> None:
        self.messages.append(message)
        self.log_trace(
            agent=message.sender,
            action=message.action,
            details=f"[{message.performative.upper()}] → {message.receiver} (status={message.status})"
        )

    def add_conflict_record(self, record: ConflictArbitrationRecord) -> None:
        self.conflict_records.append(record)
        self.log_trace(
            agent="ValidationRankingAgent",
            action="arbitrate_conflict",
            details=(
                f"Flight {record.flight_number}: "
                f"{record.newer_source} ({record.newer_quote}) superseded "
                f"{record.older_source} ({record.older_quote})"
            )
        )

    def log_trace(self, agent: str, action: str, details: str) -> None:
        self.trace_logs.append({
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
            "agent": agent,
            "action": action,
            "details": details
        })

    def clear(self) -> None:
        self.tasks.clear()
        self.messages.clear()
        self.raw_offers.clear()
        self.arbitrated_offers.clear()
        self.ranked_offers.clear()
        self.conflict_records.clear()
        self.retrieved_evidence.clear()
        self.trace_logs.clear()
