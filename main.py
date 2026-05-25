import argparse
import subprocess
import sys

COMMANDS = {
    "traffic": "traffic.py",
    "accident": "accident.py",
    "vehicle": "vehicle_name.py",
    "overspeed": "overspeed.py",
    "drowsiness": "drowsiness.py",
    "download-assets": "download_assets.py",
}


def main():
    parser = argparse.ArgumentParser(description="Run Intelligent Traffic Safety System modules.")
    parser.add_argument("command", choices=COMMANDS.keys(), help="Module to run.")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the chosen module.")
    ns = parser.parse_args()

    script = COMMANDS[ns.command]
    subprocess.run([sys.executable, script] + ns.args, check=True)


if __name__ == "__main__":
    main()
