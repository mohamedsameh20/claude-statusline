#!/usr/bin/env python3
"""Install or remove the Claude Code status line.

Copies statusline.py into your Claude config directory and points the
statusLine setting at it. Every other key in settings.json is left alone.

  python3 install.py               install (or update) the status line
  python3 install.py --uninstall   remove it again
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = "statusline.py"


def config_dir():
    # Claude Code honours CLAUDE_CONFIG_DIR; fall back to the default location.
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".claude"


def load_settings(path):
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except ValueError:
        sys.exit(f"{path} is not valid JSON. Fix it first; nothing was changed.")
    if not isinstance(data, dict):
        sys.exit(f"{path} does not contain a JSON object. Nothing was changed.")
    return data


def backup(path):
    if not path.exists():
        return None
    dst = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, dst)
    return dst


def write_settings(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def runs_python3(name):
    try:
        check = subprocess.run(
            [name, "-c", "import sys; sys.exit(sys.version_info < (3, 8))"],
            capture_output=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return check.returncode == 0


def python_command():
    """How settings.json should launch Python.

    A name on PATH survives Python upgrades, so prefer one that runs
    Python 3.8+. Windows usually has python or py rather than python3.
    Fall back to the interpreter running this installer.
    """
    for name in ("python3", "python", "py"):
        if shutil.which(name) and runs_python3(name):
            return name
    return f'"{Path(sys.executable).as_posix()}"'


def smoke_test(script):
    sample = json.dumps({
        "model": {"display_name": "Test"},
        "workspace": {"current_dir": str(Path.home())},
        "rate_limits": {"five_hour": {"used_percentage": 42, "resets_at": time.time() + 3600}},
    })
    result = subprocess.run(
        [sys.executable, str(script)],
        input=sample, capture_output=True, text=True, env={**os.environ, "COLUMNS": "120"},
    )
    if result.returncode != 0 or not result.stdout.strip():
        sys.exit(f"The status line script failed its test run:\n{result.stderr}")
    print("Test run OK.")


def install():
    cdir = config_dir()
    settings_path = cdir / "settings.json"
    target = cdir / SCRIPT
    settings = load_settings(settings_path)

    cdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / SCRIPT, target)
    smoke_test(target)

    previous = settings.get("statusLine")
    if previous:
        saved = backup(settings_path)
        print(f"Replacing your existing statusLine (backup: {saved}):\n  {previous}")

    settings["statusLine"] = {
        "type": "command",
        "command": f'{python_command()} "{target.as_posix()}"',
        "refreshInterval": 1,
    }
    write_settings(settings_path, settings)
    print(f"Installed to {target}")
    print(f"Updated {settings_path}")
    print("Open a new Claude Code session (or restart it) to see the status line.")


def uninstall():
    cdir = config_dir()
    settings_path = cdir / "settings.json"
    target = cdir / SCRIPT
    settings = load_settings(settings_path)

    line = settings.get("statusLine") or {}
    if target.as_posix() in str(line.get("command", "")):
        backup(settings_path)
        del settings["statusLine"]
        write_settings(settings_path, settings)
        print("Removed statusLine from settings.json")
    else:
        print("settings.json does not point at this status line; left it unchanged.")

    if target.exists():
        target.unlink()
        print(f"Deleted {target}")


if __name__ == "__main__":
    if "--uninstall" in sys.argv[1:]:
        uninstall()
    else:
        install()
