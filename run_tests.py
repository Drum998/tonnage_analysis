#!/usr/bin/env python3
"""Run all unit tests. Invokes pytest on the test/ directory."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    sys.exit(
        subprocess.run(
            [sys.executable, "-m", "pytest", "test/", "-v"],
            cwd=ROOT,
        ).returncode
    )
