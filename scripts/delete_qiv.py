#!/usr/bin/env python3

import os
import sys
import subprocess

def main():
    desktop_file_path = os.path.expanduser("~/.local/share/applications/qiv.desktop")
    target_dir = os.path.expanduser("~/.local/share/applications/")

    try:
        if os.path.exists(desktop_file_path):
            os.remove(desktop_file_path)
            print(f"Desktop file removed: {desktop_file_path}")
        else:
            print(f"Desktop file not found at: {desktop_file_path}")
            print("It may have already been removed or was never installed.")

        subprocess.run(["update-desktop-database", target_dir], check=True)
        print(f"Desktop database updated. 'qiv' is now uninstalled from the system.")

    except subprocess.CalledProcessError as e:
        print(f"Error updating desktop database: {e}")
        print("Make sure 'update-desktop-database' is installed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error removing .desktop file or updating database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
