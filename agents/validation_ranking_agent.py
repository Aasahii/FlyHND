from decimal import Decimal
from typing import List, Dict, Any, Optional

from models.message import AgentMessage
from models.flight import FlightOffer
from tools.fare_calculator import FareCalculator


class ValidationRankingAgent:


    def __init__(self, fare_calculator: Optional[FareCalculator] = None):
        self.name = "ValidationRankingAgent"
        self.calculator = fare_calculator or FareCalculator()

    def process_message(self, request_msg: AgentMessage) -> AgentMessage:

        if request_msg.action != "validate_and_rank":
            return AgentMessage(
                performative="FAILURE",
                sender=self.name,
                receiver=request_msg.sender,
                action=request_msg.action,
                task_id=request_msg.task_id,
                correlation_id=request_msg.correlation_id,
                status="failed",
                error_details=f"Unsupported action '{request_msg.action}' for ValidationRankingAgent."
            )

        payload = request_msg.payload
        raw_offers_data = payload.get("offers", [])
        budget_str = payload.get("budget", "30000.00")
        budget = Decimal(str(budget_str))
        top_n = int(payload.get("top_n", 3))

        offers: List[FlightOffer] = [FlightOffer.from_dict(d) for d in raw_offers_data]

        arbitrated_offers, conflict_records = self.calculator.arbitrate_offers(offers)
        price_comparison = sorted(
            arbitrated_offers,
            key=lambda offer: (offer.currency, offer.total_fare, offer.departure_time)
        )

        within_budget: List[FlightOffer] = []
        over_budget_count = 0

        for f in arbitrated_offers:
            if self.calculator.is_under_budget(f.total_fare, budget):
                within_budget.append(f)
            else:
                f.status = "FILTERED_OUT"
                over_budget_count += 1

        ranked = sorted(within_budget, key=self.calculator.calculate_rank_score)

        top_flights = ranked[:top_n]

        evidence_list = []
        for cr in conflict_records:
            evidence_list.append({
                "type": "conflict_arbitration",
                "flight_number": cr.flight_number,
                "winner_source": cr.winner_source,
                "older_quote": str(cr.older_quote),
                "newer_quote": str(cr.newer_quote),
                "fare_variance": str(cr.fare_difference),
                "rationale": cr.rationale
            })

        return AgentMessage(
            performative="INFORM",
            sender=self.name,
            receiver=request_msg.sender,
            action="validation_and_ranking_completed",
            task_id=request_msg.task_id,
            correlation_id=request_msg.correlation_id,
            status="completed",
            payload={
                "top_flights": [f.to_dict() for f in top_flights],
                "price_comparison": [f.to_dict() for f in price_comparison],
                "top_count": len(top_flights),
                "total_evaluated": len(offers),
                "arbitrated_count": len(arbitrated_offers),
                "within_budget_count": len(within_budget),
                "over_budget_count": over_budget_count,
                "budget_ceiling": str(budget),
                "conflict_records": [vars(cr) for cr in conflict_records]
            },
            evidence=evidence_list
        )
