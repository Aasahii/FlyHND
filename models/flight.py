from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any


@dataclass
class FlightOffer:

    offer_id: str
    airline: str
    airline_code: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration: str
    duration_minutes: int
    stops: int
    layovers: List[str]
    cabin: str
    baggage: str
    base_fare: Decimal
    tax_fees: Decimal
    total_fare: Decimal
    currency: str = "INR"
    source: str = "OFFLINE_DEMO"  
    observation_timestamp: str = ""
    status: str = "VALID"  
    discrepancy_note: Optional[str] = None
    fare_breakdown_available: bool = True
    segments: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        offer_id: str,
        airline: str,
        airline_code: str,
        flight_number: str,
        origin: str,
        destination: str,
        departure_time: str,
        arrival_time: str,
        duration: str,
        duration_minutes: int,
        stops: int,
        layovers: List[str],
        cabin: str,
        baggage: str,
        base_fare: Any,
        tax_fees: Any,
        currency: str = "INR",
        source: str = "OFFLINE_DEMO",
        observation_timestamp: str = "",
        status: str = "VALID",
        discrepancy_note: Optional[str] = None,
        fare_breakdown_available: bool = True,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> "FlightOffer":
        base_dec = Decimal(str(base_fare)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_dec = Decimal(str(tax_fees)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_dec = (base_dec + tax_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return cls(
            offer_id=offer_id,
            airline=airline,
            airline_code=airline_code,
            flight_number=flight_number,
            origin=origin,
            destination=destination,
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration=duration,
            duration_minutes=duration_minutes,
            stops=stops,
            layovers=layovers,
            cabin=cabin,
            baggage=baggage,
            base_fare=base_dec,
            tax_fees=tax_dec,
            total_fare=total_dec,
            currency=currency,
            source=source,
            observation_timestamp=observation_timestamp,
            status=status,
            discrepancy_note=discrepancy_note,
            fare_breakdown_available=fare_breakdown_available,
            segments=segments or []
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "airline": self.airline,
            "airline_code": self.airline_code,
            "flight_number": self.flight_number,
            "origin": self.origin,
            "destination": self.destination,
            "departure_time": self.departure_time,
            "arrival_time": self.arrival_time,
            "duration": self.duration,
            "duration_minutes": self.duration_minutes,
            "stops": self.stops,
            "layovers": self.layovers,
            "cabin": self.cabin,
            "baggage": self.baggage,
            "base_fare": str(self.base_fare),
            "tax_fees": str(self.tax_fees),
            "total_fare": str(self.total_fare),
            "total_fare_num": float(self.total_fare),
            "currency": self.currency,
            "source": self.source,
            "observation_timestamp": self.observation_timestamp,
            "status": self.status,
            "discrepancy_note": self.discrepancy_note,
            "fare_breakdown_available": self.fare_breakdown_available,
            "segments": self.segments
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlightOffer":
        return cls.create(
            offer_id=d.get("offer_id", ""),
            airline=d.get("airline", "Unknown"),
            airline_code=d.get("airline_code", "XX"),
            flight_number=d.get("flight_number", ""),
            origin=d.get("origin", ""),
            destination=d.get("destination", ""),
            departure_time=d.get("departure_time", ""),
            arrival_time=d.get("arrival_time", ""),
            duration=d.get("duration", ""),
            duration_minutes=int(d.get("duration_minutes", 0)),
            stops=int(d.get("stops", 0)),
            layovers=d.get("layovers", []),
            cabin=d.get("cabin", "Economy"),
            baggage=d.get("baggage", "7kg Cabin"),
            base_fare=d.get("base_fare", 0),
            tax_fees=d.get("tax_fees", 0),
            currency=d.get("currency", "INR"),
            source=d.get("source", "OFFLINE_DEMO"),
            observation_timestamp=d.get("observation_timestamp", ""),
            status=d.get("status", "VALID"),
            discrepancy_note=d.get("discrepancy_note"),
            fare_breakdown_available=bool(d.get("fare_breakdown_available", True)),
            segments=d.get("segments", [])
        )

    def summary_line(self, rank: int = 1) -> str:
        stops_str = "Direct" if self.stops == 0 else f"{self.stops} stop(s) via {','.join(self.layovers)}"
        return (
            f"#{rank} {self.airline} ({self.flight_number}) | "
            f"Fare: ₹{self.total_fare:,.2f} {self.currency} (Base ₹{self.base_fare:,.2f} + Tax ₹{self.tax_fees:,.2f}) | "
            f"Time: {self.departure_time} -> {self.arrival_time} ({self.duration}, {stops_str}) | "
            f"Source: [{self.source}]"
        )
