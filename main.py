import argparse
import subprocess
import sys
import os

COMMANDS = {
    "dashboard": "run.py",
    "web": "run.py",
    "traffic": "traffic.py",
    "accident": "accident.py",
    "vehicle": "vehicle_name.py",
    "overspeed": "overspeed.py",
    "drowsiness": "drowsiness.py",
    "download-assets": "download_assets.py",
}

def main():
    parser = argparse.ArgumentParser(description="Run Intelligent Traffic Safety System modules.")
    parser.add_argument(
        "command", 
        nargs="?", 
        choices=COMMANDS.keys(), 
        default="dashboard",
        help="Module to run (default: 'dashboard')"
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the chosen module.")
    ns = parser.parse_args()

    script = COMMANDS[ns.command]
    
    if ns.command in ["dashboard", "web"]:
        print("\n" + "=" * 70)
        print(">> Launching Intelligent Traffic Safety System Platform...")
        print("=" * 70)
        try:
            subprocess.run([sys.executable, script] + ns.args, check=True)
        except KeyboardInterrupt:
            print("\nApplication closed.")
    else:
        print(f"Running standalone computer vision script '{script}'...")
        subprocess.run([sys.executable, script] + ns.args, check=True)

if __name__ == "__main__":
    main()
