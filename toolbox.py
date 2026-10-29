#!/usr/bin/env python3
"""Windows Toolbox - a free, open-source Windows utility.

One menu for the jobs every Windows user needs sooner or later:
see system info, clean junk files, remove preinstalled bloatware,
manage startup apps, and install essential free software.

Safety rules, built in on purpose:
- Nothing is deleted, removed, or changed without showing you exactly
  what will happen and asking first.
- The debloat list only covers well-known preinstalled third-party
  apps, and only the ones you pick.
- Disabled startup items are backed up, so they can be restored.
- System info works on any OS. The cleanup, debloat, startup, and
  installer modules need Windows 10/11.

Requirements: Python 3.10 or newer. No third-party packages needed.
On Windows, run from a normal terminal. Some actions (removing apps,
emptying the recycle bin) may ask for administrator approval.

This tool is not affiliated with Microsoft.
"""

import ctypes
import os
import platform
import shutil
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"
VERSION = "1.0.0"


# ---------------------------------------------------------------- helpers

def clear_screen():
    if IS_WINDOWS:
        os.system("cls")
    elif os.environ.get("TERM"):
        os.system("clear")


def header(title):
    print("=" * 56)
    print("  Windows Toolbox  |  " + title)
    print("=" * 56)


def pause():
    input("\nPress Enter to go back to the menu...")


def confirm(question):
    answer = input(question + " (y/n): ").strip().lower()
    return answer == "y"


def format_bytes(num):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


def run_powershell(command):
    """Run a PowerShell command, return (returncode, stdout, stderr)."""
    full = ["powershell", "-NoProfile", "-Command", command]
    result = subprocess.run(full, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def require_windows(feature):
    if not IS_WINDOWS:
        print(f"\n{feature} needs Windows 10/11.")
        print("You are running on: " + platform.system())
        return False
    return True


# ---------------------------------------------------------------- system info

def get_ram():
    try:
        if IS_WINDOWS:
            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return status.ullTotalPhys, status.ullAvailPhys
        with open("/proc/meminfo") as f:
            values = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    values[parts[0].rstrip(":")] = int(parts[1]) * 1024
            return values.get("MemTotal", 0), values.get("MemAvailable", 0)
    except Exception:
        return 0, 0


def get_uptime():
    try:
        if IS_WINDOWS:
            ms = ctypes.windll.kernel32.GetTickCount64()
            return ms // 1000
        with open("/proc/uptime") as f:
            return int(float(f.read().split()[0]))
    except Exception:
        return 0


def system_info():
    header("System Information")
    print("\nOS:        " + platform.platform())
    print("Computer:  " + platform.node())
    print("CPU:       " + (platform.processor() or "Unknown"))
    total, free = get_ram()
    if total:
        used = total - free
        print(f"RAM:       {format_bytes(used)} used / {format_bytes(total)} total")
    uptime = get_uptime()
    days, rem = divmod(uptime, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    print(f"Uptime:    {days}d {hours}h {minutes}m")
    print("\nDrives:")
    if IS_WINDOWS:
        import string

        drives = [d + ":\\" for d in string.ascii_uppercase
                  if os.path.exists(d + ":\\")]
    else:
        drives = ["/"]
    for drive in drives:
        try:
            usage = shutil.disk_usage(drive)
            print(f"  {drive:<5} {format_bytes(usage.free)} free / "
                  f"{format_bytes(usage.total)} total")
        except Exception:
            pass


# ---------------------------------------------------------------- cleanup

def folder_size(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def clean_folder(path):
    removed = 0
    for root, _dirs, files in os.walk(path, topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(root, name))
                removed += 1
            except OSError:
                pass
    return removed


def cleanup():
    header("Disk Cleanup")
    if not require_windows("Disk cleanup"):
        return
    targets = []
    temp = os.environ.get("TEMP")
    if temp and os.path.isdir(temp):
        targets.append(("Your temp files", temp))
    windir = os.environ.get("SystemRoot", r"C:\Windows")
    win_temp = os.path.join(windir, "Temp")
    if os.path.isdir(win_temp):
        targets.append(("Windows temp files", win_temp))
    if not targets:
        print("\nNo temp folders found.")
        return
    print("\nFound:")
    for label, path in targets:
        print(f"  {label}: {path} ({format_bytes(folder_size(path))})")
    print("\nThis deletes files inside those temp folders only.")
    print("It never deletes the folders themselves.")
    if not confirm("Delete these temp files?"):
        print("Cancelled. Nothing was deleted.")
        return
    for label, path in targets:
        count = clean_folder(path)
        print(f"  {label}: {count} files removed.")
    if confirm("Also empty the Recycle Bin?"):
        code, _out, err = run_powershell("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
        if code == 0:
            print("Recycle Bin emptied.")
        else:
            print("Could not empty the Recycle Bin: " + (err or "unknown error"))


# ---------------------------------------------------------------- debloat

# Well-known preinstalled third-party apps only. System apps and
# Microsoft apps are deliberately NOT in this list.
BLOATWARE = [
    ("*CandyCrush*", "Candy Crush (preinstalled game)"),
    ("*Disney*", "Disney+ (preinstalled app)"),
    ("*Netflix*", "Netflix (preinstalled app)"),
    ("*SpotifyAB.SpotifyMusic*", "Spotify (preinstalled app)"),
    ("*TikTok*", "TikTok (preinstalled app)"),
    ("*Instagram*", "Instagram (preinstalled app)"),
    ("*Facebook*", "Facebook (preinstalled app)"),
    ("*Pinterest*", "Pinterest (preinstalled app)"),
]


def list_bloatware():
    found = []
    for pattern, label in BLOATWARE:
        code, out, _err = run_powershell(
            f"Get-AppxPackage {pattern} | Select-Object -ExpandProperty Name")
        if code == 0 and out:
            for name in out.splitlines():
                found.append((name.strip(), label))
    return found


def debloat():
    header("Remove Bloatware")
    if not require_windows("Debloat"):
        return
    print("\nScanning for preinstalled third-party apps...")
    found = list_bloatware()
    if not found:
        print("None of the listed bloatware apps are installed. Good news.")
        return
    print("\nFound on this PC:")
    for i, (name, label) in enumerate(found, 1):
        print(f"  {i}. {label} ({name})")
    print("\nEnter numbers to remove, separated by commas (or 0 to cancel).")
    choice = input("Your choice: ").strip()
    if choice == "0" or not choice:
        print("Cancelled. Nothing was removed.")
        return
    try:
        picked = [found[int(n.strip()) - 1] for n in choice.split(",")]
    except (ValueError, IndexError):
        print("Invalid choice. Nothing was removed.")
        return
    print("\nAbout to remove:")
    for name, label in picked:
        print(f"  - {label} ({name})")
    if not confirm("Remove these apps?"):
        print("Cancelled. Nothing was removed.")
        return
    for name, _label in picked:
        code, _out, err = run_powershell(
            f"Get-AppxPackage {name} | Remove-AppxPackage -ErrorAction SilentlyContinue")
        if code == 0:
            print(f"  Removed: {name}")
        else:
            print(f"  Could not remove {name}: " + (err or "unknown error"))


# ---------------------------------------------------------------- startup

def startup_entries():
    import winreg

    entries = []
    locations = [
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    ]
    for hive, path in locations:
        try:
            key = winreg.OpenKey(hive, path)
        except OSError:
            continue
        i = 0
        while True:
            try:
                name, value, _type = winreg.EnumValue(key, i)
                entries.append((hive, path, name, value))
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    return entries


def startup_manager():
    header("Startup Apps")
    if not require_windows("Startup manager"):
        return
    import winreg

    entries = startup_entries()
    if not entries:
        print("\nNo startup apps found in the Run keys.")
        return
    print("\nStartup apps:")
    for i, (_hive, _path, name, value) in enumerate(entries, 1):
        print(f"  {i}. {name}  ->  {value}")
    print("\n1. Disable an app (backed up, can be restored)")
    print("2. Restore a disabled app")
    print("0. Back")
    choice = input("Your choice: ").strip()
    if choice == "1":
        try:
            index = int(input("Number to disable: ").strip()) - 1
            hive, path, name, value = entries[index]
        except (ValueError, IndexError):
            print("Invalid choice.")
            return
        if not confirm(f"Disable '{name}' at startup?"):
            print("Cancelled.")
            return
        try:
            backup = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                      r"SOFTWARE\WindowsToolbox\Backup")
            winreg.SetValueEx(backup, name, 0, winreg.REG_SZ, value)
            winreg.CloseKey(backup)
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, name)
            winreg.CloseKey(key)
            print(f"'{name}' disabled. A backup was saved, so it can be restored.")
        except OSError as exc:
            print("Could not disable it: " + str(exc))
    elif choice == "2":
        try:
            backup = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"SOFTWARE\WindowsToolbox\Backup")
        except OSError:
            print("No backed-up startup apps found.")
            return
        names = []
        i = 0
        while True:
            try:
                name, value, _type = winreg.EnumValue(backup, i)
                names.append((name, value))
                i += 1
            except OSError:
                break
        winreg.CloseKey(backup)
        if not names:
            print("No backed-up startup apps found.")
            return
        for i, (name, _value) in enumerate(names, 1):
            print(f"  {i}. {name}")
        try:
            index = int(input("Number to restore: ").strip()) - 1
            name, value = names[index]
        except (ValueError, IndexError):
            print("Invalid choice.")
            return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            winreg.CloseKey(key)
            print(f"'{name}' restored to startup.")
        except OSError as exc:
            print("Could not restore it: " + str(exc))


# ---------------------------------------------------------------- installer

POPULAR_APPS = [
    ("Google Chrome", "Google.Chrome"),
    ("Brave Browser", "Brave.Brave"),
    ("Visual Studio Code", "Microsoft.VisualStudioCode"),
    ("VLC media player", "VideoLAN.VLC"),
    ("7-Zip", "7zip.7zip"),
    ("Notepad++", "Notepad++.Notepad++"),
    ("Git", "Git.Git"),
    ("Discord", "Discord.Discord"),
]


def installer():
    header("Install Essential Apps")
    if not require_windows("App installer"):
        return
    if shutil.which("winget") is None:
        print("\nwinget was not found on this PC.")
        print("Install App Installer from the Microsoft Store, then try again.")
        return
    print("\nPopular free apps (installed with winget):")
    for i, (label, _app_id) in enumerate(POPULAR_APPS, 1):
        print(f"  {i}. {label}")
    print("\nEnter numbers to install, separated by commas (or 0 to cancel).")
    choice = input("Your choice: ").strip()
    if choice == "0" or not choice:
        print("Cancelled. Nothing was installed.")
        return
    try:
        picked = [POPULAR_APPS[int(n.strip()) - 1] for n in choice.split(",")]
    except (ValueError, IndexError):
        print("Invalid choice. Nothing was installed.")
        return
    print("\nAbout to install:")
    for label, _app_id in picked:
        print(f"  - {label}")
    if not confirm("Install these apps?"):
        print("Cancelled.")
        return
    for label, app_id in picked:
        print(f"\nInstalling {label}...")
        result = subprocess.run(
            ["winget", "install", "--id", app_id, "-e",
             "--accept-source-agreements", "--accept-package-agreements"],
            capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  Done: {label}")
        else:
            print(f"  Failed: {label} (winget exit code {result.returncode})")


# ---------------------------------------------------------------- menu

def main():
    while True:
        clear_screen()
        print("=" * 56)
        print(f"  Windows Toolbox  v{VERSION}")
        print("  Clean junk, remove bloatware, manage startup, install apps.")
        print("=" * 56)
        print("\n  1. System information")
        print("  2. Disk cleanup (temp files, recycle bin)")
        print("  3. Remove bloatware")
        print("  4. Startup apps (disable / restore)")
        print("  5. Install essential apps (winget)")
        print("  0. Exit")
        try:
            choice = input("\nYour choice: ").strip()
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break
        clear_screen()
        if choice == "1":
            system_info()
            pause()
        elif choice == "2":
            cleanup()
            pause()
        elif choice == "3":
            debloat()
            pause()
        elif choice == "4":
            startup_manager()
            pause()
        elif choice == "5":
            installer()
            pause()
        elif choice == "0":
            print("Goodbye.")
            break
        else:
            print("Invalid choice. Please pick a number from the menu.")
            pause()


if __name__ == "__main__":
    main()
