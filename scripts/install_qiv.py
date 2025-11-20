#!/usr/bin/env python3

import os
import sys
import stat
import subprocess

def main():
    binary_name = "qiv"  
    script_dir = os.path.dirname(os.path.abspath(__file__))
    binary_path = os.path.join(script_dir, binary_name)

    if not os.path.exists(binary_path):
        print(f"Error: Binary not found at {binary_path}")
        print("Make sure the binary is in the same folder as this script.")
        sys.exit(1)

    # Temporary .desktop 
    desktop_file_path_local = os.path.join(script_dir, "qiv.desktop")

    desktop_content = f"""[Desktop Entry]
Name=Qt Image Viewer
Comment=View and edit images
Exec={binary_path} %f
Terminal=false
Type=Application
MimeType=image/jpeg;image/jpg;image/png;image/webp;image/gif;image/bmp;
Categories=Graphics;Viewer;
"""

    try:
        with open(desktop_file_path_local, 'w', encoding='utf-8') as f:
            f.write(desktop_content)

        current_permissions = os.stat(desktop_file_path_local).st_mode
        os.chmod(desktop_file_path_local, current_permissions | stat.S_IEXEC)

        print(f"Temporary desktop file created at: {desktop_file_path_local}")

        target_dir = os.path.expanduser("~/.local/share/applications/")
        os.makedirs(target_dir, exist_ok=True) 

        desktop_file_path_system = os.path.join(target_dir, "qiv.desktop")
        import shutil
        shutil.copy(desktop_file_path_local, desktop_file_path_system)

        print(f"Desktop file copied to: {desktop_file_path_system}")

        subprocess.run(["update-desktop-database", target_dir], check=True)

        print(f"Desktop database updated. 'qiv' is now integrated into the system.")
        print(f"You can now open image files with 'qiv' from your file manager.")

    except subprocess.CalledProcessError as e:
        print(f"Error updating desktop database: {e}")
        print("Make sure 'update-desktop-database' is installed (usually part of 'desktop-file-utils' package).")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error creating or installing .desktop file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
