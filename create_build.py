#!/usr/bin/env python3
"""
Build script for generating Qt resources and packaging the application with PyInstaller.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Execute a command and check its result."""
    print(f"\n>>> {description}")
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True)
        print(f"Successfully completed: {description}\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute: {description}")
        print(f"Exit code: {e.returncode}")
        print(f"Command: {' '.join(cmd)}")
        return False

def main():
    # Check if resources.qrc exists
    qrc_path = "icons/resources.qrc"
    if not os.path.exists(qrc_path):
        print(f"Resource file not found: {qrc_path}")
        print("Make sure 'icons/resources.qrc' exists in your project directory.")
        sys.exit(1)

    # Step 1: Generate Python resource module with pyside6-rcc
    if not run_command(
        ["pyside6-rcc", qrc_path, "-o", "resources_rc.py"],
        "Generating resources_rc.py from resources.qrc"
    ):
        print("\nBuild aborted due to resource generation failure.")
        sys.exit(1)

    # Step 2: Build executable with PyInstaller
    if not run_command(
        [
            "pyinstaller",
            "--noconfirm",
            "--clean",
            "--noconsole",
            #"--onefile",
            "--exclude-module=PySide6.QtNetwork",
            "main.py"
        ],
        "Building standalone executable with PyInstaller"
    ):
        print("\nBuild aborted due to PyInstaller failure.")
        sys.exit(1)

    print("\nBuild completed successfully!")
    print("Executable created in the 'dist/' folder.")

if __name__ == "__main__":
    main()