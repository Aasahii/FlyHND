"""
FlyHND 3.0 — Web Server Launcher
=================================
Run this to start the website:

    python run_web.py

Your browser will open automatically at http://localhost:5000
"""

import os
import sys
import argparse
import threading
import webbrowser
import time

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass


def main():
    parser = argparse.ArgumentParser(description="FlyHND 3.0 Web Server")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 5000)),
                        help="Port to listen on (default 5000)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't auto-open the browser")
    parser.add_argument("--debug", action="store_true",
                        help="Enable Flask debug/auto-reload")
    args = parser.parse_args()

    from web.app import app, _has_live_credentials, _provider_label

    live  = _has_live_credentials()
    url   = f"http://localhost:{args.port}"

    print()
    print("=" * 55)
    print("  FlyHND 3.0 -- Global Flight Search")
    print("=" * 55)
    print(f"  Website  : {url}")
    print(f"  Provider : {_provider_label()}")
    print(f"  Mode     : {'Live search enabled' if live else 'Demo only  (add SERPAPI_API_KEY to .env)'}")
    print("=" * 55)
    print("  Press Ctrl+C to stop the server.")
    print()

    # Open browser after a short delay to let Flask bind the port first
    if not args.no_browser and not args.debug:
        def _open():
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    app.run(host="0.0.0.0", port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
