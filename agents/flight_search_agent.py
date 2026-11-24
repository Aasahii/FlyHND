from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from models.message import AgentMessage
from models.flight import FlightOffer
from tools.flight_search_tool import FlightSearchTool


class FlightSearchAgent:


    def __init__(self, search_tool: Optional[FlightSearchTool] = None):
        self.name = "FlightSearchAgent"
        self.search_tool = search_tool or FlightSearchTool()

    def process_message(self, request_msg: AgentMessage) -> AgentMessage:
        if request_msg.action == "suggest_locations":
            payload = request_msg.payload
            try:
                suggestions = self.search_tool.suggest_locations(
                    query=str(payload.get("query", "")),
                    country=str(payload.get("country", "IN")),
                    language=str(payload.get("language", "en"))
                )
                return AgentMessage(
                    performative="INFORM",
                    sender=self.name,
                    receiver=request_msg.sender,
                    action="suggest_locations_completed",
                    task_id=request_msg.task_id,
                    correlation_id=request_msg.correlation_id,
                    status="completed",
                    payload={"suggestions": suggestions, "suggestions_count": len(suggestions)}
                )
            except Exception as exc:
                return AgentMessage(
                    performative="FAILURE",
                    sender=self.name,
                    receiver=request_msg.sender,
                    action="suggest_locations_failed",
                    task_id=request_msg.task_id,
                    correlation_id=request_msg.correlation_id,
                    status="failed",
                    error_details=str(exc)
                )

        if request_msg.action != "search_flights":
            return AgentMessage(
                performative="FAILURE",
                sender=self.name,
                receiver=request_msg.sender,
                action=request_msg.action,
                task_id=request_msg.task_id,
                correlation_id=request_msg.correlation_id,
                status="failed",
                error_details=f"Unsupported action '{request_msg.action}' for FlightSearchAgent."
            )

        payload = request_msg.payload
        origin = payload.get("origin", "PNQ")
        destination = payload.get("destination", "SIN")
        departure_date = payload.get("departure_date", "")
        mode = payload.get("mode", "offline")
        adults = payload.get("adults", 1)
        currency = payload.get("currency", "INR")

        offers, recovery_trace = self.search_tool.search(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            mode=mode,
            adults=adults,
            currency=currency
        )

        offers_data = [o.to_dict() for o in offers]

        return AgentMessage(
            performative="INFORM",
            sender=self.name,
            receiver=request_msg.sender,
            action="search_flights_completed",
            task_id=request_msg.task_id,
            correlation_id=request_msg.correlation_id,
            status="completed",
            payload={
                "offers": offers_data,
                "offers_count": len(offers),
                "mode": mode,
                "recovery_trace": recovery_trace
            },
            evidence=[
                {
                    "type": "retrieval_trace",
                    "step_count": len(recovery_trace),
                    "steps": recovery_trace
                }
            ]
        )
