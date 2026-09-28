"""
run_kall.py
===========
One-command launcher for the KALL Top-Secret Millimeter-Wave Defense Portal.
Starts the high-performance Tornado server and opens the operator HUD in the default web browser.

Usage:
    python run_kall.py [--port 8080] [--no-browser]
"""

import argparse
import os
import sys
import time
import webbrowser
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import kall_server
import tornado.ioloop


def main():
    parser = argparse.ArgumentParser(description="KALL Top Security Portal Launcher")
    parser.add_argument("--port", type=int, default=8080, help="Port to host KALL (default: 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch browser")
    args = parser.parse_args()

    port = args.port
    host = args.host
    url = f"http://localhost:{port}"

    print()
    print("*" * 76)
    print("  KALL // CLASSIFIED MILLIMETER-WAVE HOLOGRAPHIC DEFENSE PORTAL")
    print("  SECURITY CLASSIFICATION: TOP SECRET // NOFORN // SPECIAL ACCESS REQUIRED")
    print("*" * 76)
    print(f"  [+] Host URL:              {url}")
    print(f"  [+] Physics Core:          Sheen et al. (2001) 3-D Holographic Reconstruction")
    print(f"  [+] AI Threat Detection:   PyTorch ConvDetector (Lightweight CNN)")
    print(f"  [+] Holographic 3-D Engine: Pure Canvas2D Vector & Voxel Matrix Engine (100% Offline)")
    print("*" * 76)

    app = kall_server.make_app()
    app.listen(port, address=host)

    if not args.no_browser:
        def open_browser():
            time.sleep(0.8)
            print(f"  [>] Opening KALL Tactical Console in default browser: {url}")
            webbrowser.open(url)

        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    print("  [+] KALL Server online. Press CTRL+C to terminate.")
    print("*" * 76)
    print()

    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        print("\n  [!] KALL Server terminated by operator.")


if __name__ == "__main__":
    main()
