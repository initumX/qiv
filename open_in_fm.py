import platform, subprocess, os

def open_path_in_file_manager(file_path: str):
    """Open file in file manager with selection, if supported."""
    system = platform.system()
    file_path = os.path.abspath(file_path)
    folder = os.path.dirname(file_path)

    try:
        if system == "Windows":
            subprocess.run(["explorer", "/select,", file_path], check=True)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", "-R", file_path], check=True)
        else:  # Linux
            # Try specific file managers via D-Bus
            file_uri = f"file://{file_path}"
            folder_uri = f"file://{folder}"

            # Nautilus, Nemo, Caja
            try:
                subprocess.run([
                    "dbus-send", "--print-reply", "--dest=org.freedesktop.FileManager1",
                    "/org/freedesktop/FileManager1",
                    "org.freedesktop.FileManager1.ShowItems",
                    f"array:string:{file_uri}", "string:\"\""
                ], check=True)
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            # Dolphin (KDE)
            try:
                subprocess.run([
                    "dbus-send", "--print-reply", "--dest=org.freedesktop.DBus",
                    "--type=method_call", "--reply-timeout=1000",
                    "/Application", "org.qtproject.Qt.QApplication.quit"
                ], check=False)  # Ignore, just to check if dbus-send exists

                subprocess.run([
                    "dbus-send", "--print-reply",
                    "--dest=org.kde.dolphin",
                    "/dolphin/Dolphin_1",
                    "org.kde.dolphin.DolphinApplication.openUrl",
                    f"string:{folder_uri}"
                ], check=True)
                # Dolphin doesn't support selection via dbus easily → open folder
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            # Thunar (XFCE) — no selection via CLI, but can open folder
            if os.path.exists("/usr/bin/thunar"):
                subprocess.run(["thunar", folder], check=True)
                return

            # Fallback: open folder with xdg-open
            subprocess.run(["xdg-open", folder], check=True)

    except Exception:
        # Last resort: just open folder
        try:
            if system == "Windows":
                os.startfile(folder)
            elif system == "Darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception:
            pass