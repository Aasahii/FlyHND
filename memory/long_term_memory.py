import json
import os
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional

from memory.tfidf_retriever import TFIDFRetriever, RetrievedEvidence
from models.flight import FlightOffer
from models.memory_models import SearchRequest


DEFAULT_POLICIES = [
    {
        "category": "travel_policy",
        "title": "Corporate International Airfare Ceiling Policy (Pune to Singapore)",
        "content": (
            "Standard economy airfare ceiling for Pune (PNQ) to Singapore (SIN) travel is capped at "
            "INR 30,000 per passenger. Any flight exceeding INR 30,000 is classified as out-of-policy "
            "and must be filtered out unless executive override is provided. Direct and one-stop flights "
            "under 30000 INR are preferred."
        )
    },
    {
        "category": "travel_policy",
        "title": "Fare Staleness and Provenance Arbitration Policy",
        "content": (
            "When duplicate flight offers or conflicting price quotes exist across providers and local cache, "
            "agents must compare observation timestamps. The newest provider quote supersedes older cache "
            "quotes. All discrepancies between cached and live fares must be logged in the audit trail."
        )
    },
    {
        "category": "travel_policy",
        "title": "Baggage and Transit Allowance Requirements (Southeast Asia Transit)",
        "content": (
            "Transit routes via Kuala Lumpur (KUL) or Chennai (MAA) must verify minimum 7kg cabin baggage "
            "and standard checked baggage allowance. Ancillary baggage charges must be incorporated into "
            "total fare calculation where mandatory."
        )
    },
    {
        "category": "governance",
        "title": "Human-in-the-Loop Email Dispatch and Non-Booking Mandate",
        "content": (
            "AI agents possess read-only search permissions and local drafting permissions. External email "
            "dispatch requires explicit, interactive human confirmation at the moment of sending. Automated "
            "financial transactions, ticketing, or simulated booking confirmations are strictly prohibited."
        )
    }
]

DEFAULT_HISTORICAL_CASES = [
    {
        "correlation_id": "case-hist-20261015-01",
        "route": "Pune -> Singapore",
        "departure_date": "2026-10-15",
        "budget": 30000.0,
        "selected_fare": 24200.0,
        "selected_airline": "Scoot (FL-101)",
        "source": "HISTORICAL_RECORD",
        "notes": "Previous query for Pune to Singapore completed under budget at INR 24,200 via Scoot FL-101."
    },
    {
        "correlation_id": "case-hist-20260920-02",
        "route": "Pune -> Singapore",
        "departure_date": "2026-09-20",
        "budget": 35000.0,
        "selected_fare": 26100.0,
        "selected_airline": "IndiGo (FL-205)",
        "source": "HISTORICAL_RECORD",
        "notes": "Historical IndiGo 1-stop via MAA selected at INR 26,100 within INR 35,000 cap."
    }
]


class LongTermMemoryStore:
    """
    Persistent SQLite storage and TF-IDF semantic retrieval engine for FlyHND.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "data", "flyhnd_memory.db")
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self, force_reset: bool = False) -> None:
        """Initialize SQLite database schema and seed default policies if empty."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cur = conn.cursor()
            if force_reset:
                cur.execute("DROP TABLE IF EXISTS policies")
                cur.execute("DROP TABLE IF EXISTS search_cases")
                cur.execute("DROP TABLE IF EXISTS flight_cache")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS search_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id TEXT NOT NULL,
                    route TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date TEXT NOT NULL,
                    budget REAL NOT NULL,
                    selected_fare REAL,
                    selected_airline TEXT,
                    source TEXT NOT NULL,
                    notes TEXT,
                    results_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS flight_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    offer_id TEXT NOT NULL,
                    airline TEXT NOT NULL,
                    airline_code TEXT NOT NULL,
                    flight_number TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_time TEXT NOT NULL,
                    arrival_time TEXT NOT NULL,
                    duration TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    stops INTEGER NOT NULL,
                    layovers TEXT NOT NULL,
                    cabin TEXT NOT NULL,
                    baggage TEXT NOT NULL,
                    base_fare REAL NOT NULL,
                    tax_fees REAL NOT NULL,
                    total_fare REAL NOT NULL,
                    currency TEXT NOT NULL,
                    source TEXT NOT NULL,
                    observation_timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

            cur.execute("SELECT COUNT(*) FROM policies")
            if cur.fetchone()[0] == 0:
                now_str = datetime.now(timezone.utc).isoformat()
                for p in DEFAULT_POLICIES:
                    cur.execute(
                        "INSERT INTO policies (category, title, content, created_at) VALUES (?, ?, ?, ?)",
                        (p["category"], p["title"], p["content"], now_str)
                    )
                for c in DEFAULT_HISTORICAL_CASES:
                    cur.execute("""
                        INSERT INTO search_cases (
                            correlation_id, route, origin, destination, departure_date,
                            budget, selected_fare, selected_airline, source, notes, results_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        c["correlation_id"], c["route"], "PNQ", "SIN", c["departure_date"],
                        c["budget"], c["selected_fare"], c["selected_airline"], c["source"],
                        c["notes"], "[]", now_str
                    ))
                conn.commit()

    def reset_database(self) -> None:
        """Reset database to factory clean state with seed records."""
        self._init_db(force_reset=True)

    def retrieve_relevant_evidence(self, query_text: str, top_k: int = 3) -> List[RetrievedEvidence]:
        """
        Extract policy documents and prior resolved cases from SQLite,
        build a sparse TF-IDF index, and evaluate cosine similarity.
        """
        corpus: List[Dict[str, Any]] = []

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, category, title, content FROM policies")
            for row in cur.fetchall():
                corpus.append({
                    "id": f"policy-{row['id']}",
                    "category": row["category"],
                    "title": row["title"],
                    "content": row["content"],
                    "metadata": {"type": "policy", "source_table": "policies"}
                })

            cur.execute("""
                SELECT id, correlation_id, route, departure_date, budget,
                       selected_fare, selected_airline, notes FROM search_cases
            """)
            for row in cur.fetchall():
                content = (
                    f"Route: {row['route']}, Date: {row['departure_date']}, "
                    f"Budget: INR {row['budget']}, Result: {row['selected_airline']} "
                    f"at INR {row['selected_fare']}. {row['notes'] or ''}"
                )
                corpus.append({
                    "id": f"case-{row['id']}",
                    "category": "historical_case",
                    "title": f"Previous Search: {row['route']} ({row['departure_date']})",
                    "content": content,
                    "metadata": {
                        "type": "case",
                        "correlation_id": row["correlation_id"],
                        "budget": row["budget"],
                        "selected_fare": row["selected_fare"]
                    }
                })

        if not corpus:
            return []

        retriever = TFIDFRetriever().fit(corpus)
        return retriever.query(query_text, top_k=top_k)

    def save_search_case(
        self,
        request: SearchRequest,
        top_offers: List[FlightOffer],
        source: str = "COMPLETED_SEARCH"
    ) -> int:
        """Persist a completed flight search run into long-term SQLite memory."""
        now_str = datetime.now(timezone.utc).isoformat()
        results_json = json.dumps([o.to_dict() for o in top_offers])
        selected_fare = float(top_offers[0].total_fare) if top_offers else None
        selected_airline = f"{top_offers[0].airline} ({top_offers[0].flight_number})" if top_offers else None
        notes = f"Top {len(top_offers)} flights retrieved under INR {request.budget} cap."

        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO search_cases (
                    correlation_id, route, origin, destination, departure_date,
                    budget, selected_fare, selected_airline, source, notes, results_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"case-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                request.route,
                request.origin,
                request.destination,
                request.departure_date,
                float(request.budget),
                selected_fare,
                selected_airline,
                source,
                notes,
                results_json,
                now_str
            ))
            conn.commit()
            return cur.lastrowid

    def seed_cached_flights(self, offers: List[FlightOffer]) -> None:
        """Populate or update SQLite flight cache with snapshot offers."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            for o in offers:
                cur.execute("""
                    INSERT INTO flight_cache (
                        offer_id, airline, airline_code, flight_number, origin, destination,
                        departure_time, arrival_time, duration, duration_minutes, stops,
                        layovers, cabin, baggage, base_fare, tax_fees, total_fare,
                        currency, source, observation_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    o.offer_id, o.airline, o.airline_code, o.flight_number, o.origin, o.destination,
                    o.departure_time, o.arrival_time, o.duration, o.duration_minutes, o.stops,
                    json.dumps(o.layovers), o.cabin, o.baggage, float(o.base_fare), float(o.tax_fees),
                    float(o.total_fare), o.currency, "OFFLINE_CACHE", o.observation_timestamp
                ))
            conn.commit()

    def get_cached_flights(self, origin: str, destination: str) -> List[FlightOffer]:
        """Retrieve cached flight snapshot offers from SQLite."""
        offers: List[FlightOffer] = []
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM flight_cache
                WHERE origin = ? AND destination = ?
                ORDER BY total_fare ASC
            """, (origin, destination))
            for row in cur.fetchall():
                layovers = json.loads(row["layovers"]) if row["layovers"] else []
                offer = FlightOffer.create(
                    offer_id=row["offer_id"],
                    airline=row["airline"],
                    airline_code=row["airline_code"],
                    flight_number=row["flight_number"],
                    origin=row["origin"],
                    destination=row["destination"],
                    departure_time=row["departure_time"],
                    arrival_time=row["arrival_time"],
                    duration=row["duration"],
                    duration_minutes=row["duration_minutes"],
                    stops=row["stops"],
                    layovers=layovers,
                    cabin=row["cabin"],
                    baggage=row["baggage"],
                    base_fare=row["base_fare"],
                    tax_fees=row["tax_fees"],
                    currency=row["currency"],
                    source="OFFLINE_CACHE",
                    observation_timestamp=row["observation_timestamp"],
                    status="VALID"
                )
                offers.append(offer)
        return offers

    def inspect_history(self) -> List[Dict[str, Any]]:
        """Return all historical search cases stored in SQLite."""
        history = []
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, correlation_id, route, departure_date, budget,
                       selected_fare, selected_airline, source, notes, created_at
                FROM search_cases ORDER BY id DESC
            """)
            for row in cur.fetchall():
                history.append(dict(row))
        return history

    def clear_history(self) -> int:
        """Clear historical search records (preserves policy corpus)."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM search_cases")
            conn.commit()
            return cur.rowcount
