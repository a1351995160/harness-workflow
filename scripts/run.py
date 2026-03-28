#!/usr/bin/env python3
"""Wrapper script for harness-workflow Python scripts.

Handles Python environment setup and delegates to the target script.
Usage: python run.py <script_name> [args...]
"""

import subprocess
import sys
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <script_name> [args...]")
        print(f"Available scripts: {', '.join(f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py') and f != 'run.py')}")
        sys.exit(1)

    script_name = sys.argv[1]
    script_path = os.path.join(SCRIPTS_DIR, script_name)

    if not os.path.isfile(script_path):
        print(f"Error: Script '{script_name}' not found in {SCRIPTS_DIR}")
        sys.exit(1)

    # Pass remaining args to the target script
    result = subprocess.run(
        [sys.executable, script_path] + sys.argv[2:],
        cwd=os.getcwd(),
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
