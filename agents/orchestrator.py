import uuid
from decimal import Decimal
from typing import Optional, Dict, Any, List, Callable

from models.message import AgentMessage
from models.flight import FlightOffer
from models.memory_models import SearchRequest, TaskRecord
from memory.working_memory import WorkingMemory
from memory.long_term_memory import LongTermMemoryStore
from agents.flight_search_agent import FlightSearchAgent
from agents.policy_memory_agent import PolicyMemoryAgent
from agents.validation_ranking_agent import ValidationRankingAgent


class RequestCoordinator:

    def __init__(
        self,
        long_term_memory: Optional[LongTermMemoryStore] = None,
        search_agent: Optional[FlightSearchAgent] = None,
        policy_agent: Optional[PolicyMemoryAgent] = None,
        validation_agent: Optional[ValidationRankingAgent] = None,
    ):
        self.name = "RequestCoordinator"
        self.ltm = long_term_memory or LongTermMemoryStore()
        self.flight_search_agent = search_agent or FlightSearchAgent()
        self.policy_memory_agent = policy_agent or PolicyMemoryAgent(self.ltm)
        self.validation_ranking_agent = validation_agent or ValidationRankingAgent()
        self.working_memory: Optional[WorkingMemory] = None

    def execute_workflow(
        self,
        search_request: SearchRequest,
        mode: str = "offline",
    ) -> Dict[str, Any]:
    

        correlation_id = f"flyhnd-{uuid.uuid4().hex[:8]}"
        self.working_memory = WorkingMemory(correlation_id=correlation_id)
        self.working_memory.set_request(search_request)

        task_policy_id = f"task-policy-{uuid.uuid4().hex[:4]}"
        self.working_memory.register_task(
            task_id=task_policy_id,
            owner=self.policy_memory_agent.name,
            action="retrieve_policy_and_cases"
        )

        msg_policy_req = AgentMessage(
            performative="REQUEST",
            sender=self.name,
            receiver=self.policy_memory_agent.name,
            action="retrieve_policy_and_cases",
            task_id=task_policy_id,
            correlation_id=correlation_id,
            payload={
                "query": f"{search_request.route} flight",
                "top_k": 3
            }
        )
        self.working_memory.add_message(msg_policy_req)
        msg_policy_resp = self.policy_memory_agent.process_message(msg_policy_req)
        self.working_memory.add_message(msg_policy_resp)
        self.working_memory.update_task_status(
            task_id=task_policy_id,
            status=msg_policy_resp.status,
            summary=f"Retrieved {len(msg_policy_resp.evidence)} relevant records."
        )

        task_search_id = f"task-search-{uuid.uuid4().hex[:4]}"
        self.working_memory.register_task(
            task_id=task_search_id,
            owner=self.flight_search_agent.name,
            action="search_flights"
        )

        msg_search_req = AgentMessage(
            performative="REQUEST",
            sender=self.name,
            receiver=self.flight_search_agent.name,
            action="search_flights",
            task_id=task_search_id,
            correlation_id=correlation_id,
            payload={
                "origin": search_request.origin,
                "destination": search_request.destination,
                "departure_date": search_request.departure_date,
                "currency": search_request.currency,
                "mode": mode,
                "adults": search_request.passengers
            }
        )
        self.working_memory.add_message(msg_search_req)
        msg_search_resp = self.flight_search_agent.process_message(msg_search_req)
        self.working_memory.add_message(msg_search_resp)

        raw_offers_data = msg_search_resp.payload.get("offers", [])
        self.working_memory.raw_offers = [FlightOffer.from_dict(d) for d in raw_offers_data]
        self.working_memory.update_task_status(
            task_id=task_search_id,
            status=msg_search_resp.status,
            summary=f"Obtained {len(raw_offers_data)} candidate offers (mode={mode})."
        )

        task_rank_id = f"task-rank-{uuid.uuid4().hex[:4]}"
        self.working_memory.register_task(
            task_id=task_rank_id,
            owner=self.validation_ranking_agent.name,
            action="validate_and_rank"
        )

        msg_rank_req = AgentMessage(
            performative="REQUEST",
            sender=self.name,
            receiver=self.validation_ranking_agent.name,
            action="validate_and_rank",
            task_id=task_rank_id,
            correlation_id=correlation_id,
            payload={
                "offers": raw_offers_data,
                "budget": str(search_request.budget),
                "top_n": 3
            }
        )
        self.working_memory.add_message(msg_rank_req)
        msg_rank_resp = self.validation_ranking_agent.process_message(msg_rank_req)
        self.working_memory.add_message(msg_rank_resp)

        top_flights_data = msg_rank_resp.payload.get("top_flights", [])
        top_flights = [FlightOffer.from_dict(d) for d in top_flights_data]
        self.working_memory.ranked_offers = top_flights
        self.working_memory.update_task_status(
            task_id=task_rank_id,
            status=msg_rank_resp.status,
            summary=(
                f"Ranked {len(top_flights)} qualifying options. "
                f"Over-budget filtered: {msg_rank_resp.payload.get('over_budget_count', 0)}."
            )
        )

        source_label = (
            "LIVE_API" if mode == "live"
            else "OFFLINE_CACHE" if mode == "simulate_failure"
            else "OFFLINE_DEMO"
        )
        try:
            self.ltm.save_search_case(
                request=search_request,
                top_offers=top_flights,
                source=source_label
            )
        except Exception:
            pass

        recovery_trace = msg_search_resp.payload.get("recovery_trace", [])

        report = {
            "correlation_id": correlation_id,
            "request": search_request.to_dict(),
            "mode": mode,
            "top_flights": [f.to_dict() for f in top_flights],
            "price_comparison": msg_rank_resp.payload.get("price_comparison", []),
            "recovery_trace": recovery_trace,
            "retrieved_policies": msg_policy_resp.evidence,
            "conflict_arbitration": msg_rank_resp.evidence,
            "filter_summary": {
                "total_evaluated": msg_rank_resp.payload.get("total_evaluated"),
                "within_budget": msg_rank_resp.payload.get("within_budget_count"),
                "over_budget_filtered": msg_rank_resp.payload.get("over_budget_count"),
                "budget_ceiling": str(search_request.budget)
            },
            "messages": [m.to_dict() for m in self.working_memory.messages],
            "trace_logs": self.working_memory.trace_logs
        }

        self.working_memory.clear()
        return report
