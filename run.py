import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app

app = create_app()

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print("\n" + "=" * 70)
    print(">> INTELLIGENT TRAFFIC SAFETY SYSTEM")
    print("   Smart Vision. Safer Roads. Intelligent Monitoring.")
    print("=" * 70)
    print(f" * Server running on: http://{host}:{port}")
    print(" * Press CTRL+C to stop the server\n")
    app.run(host=host, port=port, debug=False, threaded=True)
