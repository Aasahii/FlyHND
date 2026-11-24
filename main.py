"""
FlyHND — Command-line entry point
----------------------------------
Primary interface: run_web.py  (opens the website)
This file keeps a minimal offline demo mode for quick testing.

Usage:
  python run_web.py          ← start the website (recommended)
  python main.py --demo      ← offline CLI demo (Pune→Singapore benchmark)
  python main.py --live      ← live CLI search (requires .env credentials)
"""

import argparse
import os
import sys
from datetime import datetime
from decimal import Decimal

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from models.memory_models import SearchRequest
from agents.orchestrator import RequestCoordinator


def run_search(origin, destination, date, budget=None, mode="offline", passengers=1, currency="INR"):
    req = SearchRequest(
        origin=origin,
        destination=destination,
        departure_date=date,
        budget=Decimal(str(budget)) if budget else Decimal("9999999.00"),
        passengers=passengers,
        currency=currency,
    )
    coordinator = RequestCoordinator()
    report = coordinator.execute_workflow(search_request=req, mode=mode)

    offers = sorted(
        report.get("price_comparison", []),
        key=lambda x: float(x.get("total_fare_num", x.get("total_fare", 0)))
    )

    print(f"\n{'='*70}")
    print(f"  FlyHND Results: {req.route}  |  {date}  |  Mode: {mode.upper()}")
    print(f"{'='*70}")

    if not offers:
        print("  No flights found.")
        return

    for i, o in enumerate(offers, 1):
        stops = int(o.get("stops", 0))
        stops_str = "Direct" if stops == 0 else f"{stops} stop(s) via {', '.join(o.get('layovers', []))}"
        print(
            f"\n  #{i}  {o['airline']} {o['flight_number']}\n"
            f"       Fare : {o['currency']} {float(o['total_fare']):,.0f}\n"
            f"       Time : {o['departure_time']} → {o['arrival_time']}  ({o['duration']})\n"
            f"       Route: {stops_str}\n"
            f"       Source: {o['source']}"
        )

    print(f"\n{'='*70}")
    print("  Tip: Run  python run_web.py  to use the full web interface.")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="FlyHND — Flight Search (CLI mode)",
        epilog="For the web interface, run:  python run_web.py"
    )
    parser.add_argument("--demo", action="store_true",
                        help="Run offline demo: Pune → Singapore (no credentials needed)")
    parser.add_argument("--live", action="store_true",
                        help="Run live search using SERPAPI_API_KEY from .env")
    parser.add_argument("--from", dest="origin", default="PNQ",
                        help="Origin IATA code (default: PNQ)")
    parser.add_argument("--to", dest="destination", default="SIN",
                        help="Destination IATA code (default: SIN)")
    parser.add_argument("--date", default=None,
                        help="Departure date YYYY-MM-DD (default: tomorrow)")
    parser.add_argument("--budget", type=float, default=None,
                        help="Max fare ceiling")
    parser.add_argument("--passengers", type=int, default=1)
    parser.add_argument("--currency", default="INR")
    args = parser.parse_args()

    date = args.date or datetime.today().strftime("%Y-%m-") + str(datetime.today().day + 1).zfill(2)

    if args.live:
        if not os.getenv("SERPAPI_API_KEY") and not os.getenv("AMADEUS_CLIENT_ID"):
            print("\n[!] No live provider configured. Add SERPAPI_API_KEY to .env\n")
            sys.exit(1)
        run_search(args.origin, args.destination, date, args.budget, "live", args.passengers, args.currency)
        return

    if args.demo or True:   # default action if no flags given
        print("\n  Running offline demo (Pune → Singapore benchmark).")
        print("  For the web interface, run:  python run_web.py\n")
        run_search("PNQ", "SIN", date or "2027-01-15", 30000, "offline")


if __name__ == "__main__":
    main()
