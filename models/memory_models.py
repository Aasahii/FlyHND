from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Dict, Any


@dataclass
class SearchRequest:

    # IATA airport codes or Google Flights location IDs (kgmids).
    origin: str = "PNQ"
    destination: str = "SIN"
    departure_date: str = ""
    budget: Decimal = field(default_factory=lambda: Decimal("30000.00"))
    passengers: int = 1
    currency: str = "INR"
    trip_type: str = "ONE_WAY"
    route: str = ""

    def __post_init__(self):
        if not self.route:
            self.route = f"{self.origin} -> {self.destination}"
        if not isinstance(self.budget, Decimal):
            self.budget = Decimal(str(self.budget))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "departure_date": self.departure_date,
            "budget": str(self.budget),
            "passengers": self.passengers,
            "currency": self.currency,
            "trip_type": self.trip_type,
            "route": self.route,
        }


@dataclass
class TaskRecord:

    task_id: str
    owner: str
    action: str
    status: str = "assigned"  
    result_summary: Optional[str] = None
    timestamp: str = ""


@dataclass
class ConflictArbitrationRecord:

    flight_number: str
    older_quote: Decimal
    older_source: str
    older_timestamp: str
    newer_quote: Decimal
    newer_source: str
    newer_timestamp: str
    winner_source: str
    fare_difference: Decimal
    rationale: str
