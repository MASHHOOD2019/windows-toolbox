# Windows Toolbox

A free, open-source Windows utility. One menu for the jobs every Windows user needs sooner or later: see system info, clean junk files, remove preinstalled bloatware, manage startup apps, and install essential free software.

## Features

- **System information** - OS, CPU, RAM usage, uptime, and free disk space.
- **Disk cleanup** - Removes temp files and optionally empties the Recycle Bin.
- **Remove bloatware** - Lists well-known preinstalled third-party apps (Candy Crush, Disney+, Netflix, Spotify, TikTok, and more) and removes only the ones you pick.
- **Startup apps** - Lists startup apps, disables them with a backup, and restores them later.
- **Install essential apps** - Installs popular free software (Chrome, VS Code, VLC, 7-Zip, Git, and more) through winget.

## Safety

Nothing is deleted, removed, or changed without showing you exactly what will happen and asking first. The debloat list only covers well-known preinstalled third-party apps, never system apps. Disabled startup items are backed up so they can be restored.

## Requirements

- Windows 10 or 11
- Python 3.10 or newer
- No third-party packages needed

## How to run

```bash
python toolbox.py
```

Pick a number from the menu. Every destructive action asks for confirmation first.

## How it works

```
Main menu
  ├── 1. System information
  ├── 2. Disk cleanup (temp files, recycle bin)
  ├── 3. Remove bloatware (PowerShell Appx list, your picks only)
  ├── 4. Startup apps (Run keys, with backup and restore)
  └── 5. Install essential apps (winget)
```

## Roadmap

- One-click restore point before changes
- Simple graphical interface
- More cleanup targets (browser caches, update leftovers)

## License

MIT. This tool is not affiliated with Microsoft.
