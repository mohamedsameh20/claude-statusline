# claude-statusline

A two-row status line for [Claude Code](https://claude.com/claude-code). It shows the model and effort level, your context window, your 5-hour and weekly limits with reset times, prompt-cache status, session cost, lines changed, and the current directory.

```
✻ Opus 5.5  high ●●●○○       │  5h ▰▰▰▱▱▱▱▱▱▱  34% ↻ 2h10m 16:40     │  ● cache 91% 42m  ·  $0.42  ·  +156 −23
ctx ▰▱▱▱▱▱▱▱▱▱  10% 99k/1.0M │  7d ▰▰▰▰▰▰▰▰▱▱  81% ↻ 3d4h Sun 07:00  │  ~/project  ⎇ wt  ◇ agent
```

Bars shift from sage to amber to coral as they fill. Anything at 90% or more pulses, and a cache that is about to expire turns amber.

It is a single Python file with no dependencies and no network access. It reads the session JSON that Claude Code passes on stdin, and it fits the terminal width by dropping to a compact layout when space runs short.

## Requirements

- Claude Code
- Python 3.8 or newer. The script uses only the standard library, so there is nothing else to install.
- macOS or Linux. Windows should work but is untested.

### Why Python?

Python is already installed on most developer machines, and it makes the colour gradients, column alignment and narrow-terminal fallback easy to write. A shell version would need `jq` and would be much harder to maintain.

The installer looks for a Python 3 command on your PATH. It tries `python3`, then `python`, then `py`, and writes the first one that works into `settings.json`. It uses a command name instead of a full path so the status line keeps working after Python is upgraded.
- A terminal with 24-bit colour, which most modern terminals support.

## Install

### Option A: ask Claude Code to do it

Open Claude Code and paste this:

> Set up the Claude Code status line from https://github.com/mohamedsameh20/claude-statusline. Follow the "For Claude Code" section of its README.

If you don't have Python, Claude will offer to install it and ask first. On Windows, you can choose between Python and uv.

### Option B: by hand

```sh
git clone https://github.com/mohamedsameh20/claude-statusline.git
cd claude-statusline
python3 install.py
```

On Windows, use `python install.py` or `py install.py` instead. Then open a new Claude Code session.

## For Claude Code

If a user has asked you to set this up, do the following. Only change the status line. Leave every other setting alone.

1. Work out the config directory. Use `$CLAUDE_CONFIG_DIR` if it is set, otherwise `~/.claude`. Call it `CONFIG`.
2. Read `CONFIG/settings.json` if it exists. If it already has a `statusLine` key, show the user its current value and ask whether to replace it. The installer backs up the file first, but still ask before replacing.
3. Find a Python 3.8+ command. Try `python3`, `python`, then `py` with `--version`. On Windows, a `python3` that opens the Microsoft Store does not count. If one works, go to step 5.
4. If none works, tell the user the status line needs Python and offer to install it. Install nothing until they agree.
   - **Windows:** ask the user to choose between Python and uv, and recommend the lighter one for their machine:
     - **uv is already installed** (`uv --version` works): recommend uv, because it only has to download Python. Run `uv python install 3.12 --default`, then `uv python update-shell`.
     - **uv is not installed:** recommend Python, because the uv route installs two things (uv, then a Python through it). Run `winget install -e --id Python.Python.3.12`. This also installs the `py` launcher.
     - **They choose uv anyway:** run `winget install -e --id astral-sh.uv`, then the two uv commands above.
   - **macOS:** `xcode-select --install`, or `brew install python` if they use Homebrew.
   - **Linux:** the distro package, for example `sudo apt install python3` or `sudo dnf install python3`.

   A fresh install is often missing from the current shell's PATH. If no Python command is found afterwards, ask the user to restart Claude Code and paste the setup request again. The new session starts from step 1. Running `install.py` from a shell that can't find Python by name writes a full interpreter path into settings, and that path can break after an upgrade.
5. Clone the repo into a temporary directory:
   `git clone https://github.com/mohamedsameh20/claude-statusline.git "$(mktemp -d)/claude-statusline"`
6. Read `install.py` and `statusline.py` from the clone. Then run `install.py` from inside it with the command from step 3. The installer copies `statusline.py` to `CONFIG`, adds a `statusLine` entry to `CONFIG/settings.json`, keeps every other key, and runs a test render. If the test fails, show the error and stop.
7. Tell the user the status line will appear in the next session and that running `install.py --uninstall` with the same Python command removes it.

Do not hand-edit `settings.json` unless the installer fails. If you have to, merge the entry in. Do not overwrite the whole file.

## Customise

Everything you might want to change is a constant near the top of `statusline.py`:

| Constant | Default | What it does |
|---|---|---|
| `BAR_WIDTH` | `10` | Width of the full meter bars |
| `ALERT_PCT` | `90` | Usage percentage at which a meter starts pulsing |
| `CACHE_ALERT_SECS` | `300` | Seconds left on the prompt cache before it turns amber |
| `PULSE_PERIOD` | `4` | Seconds for one pulse cycle |
| `DIR_MAX` | `28` | Longest directory path shown before truncating |
| `GRADIENT` | sage → amber → coral | Colours that bars move through |

After editing, run `python3 install.py` again to copy the new version over.

## Troubleshooting

- **Nothing shows up.** Look at the `statusLine.command` value in `settings.json` and run that exact command with some input, for example `echo '{}' | python3 ~/.claude/statusline.py`. You should see output. If you don't, the error is printed. If the Python command isn't found, install Python 3 and run `install.py` again.
- **The 5h and 7d meters are missing.** Claude Code only sends rate-limit data on some plans. The script hides a meter it has no data for.
- **Rows wrap or look misaligned.** Widen the terminal. The script switches to a narrower layout automatically, but it has to know the terminal width.
- **You want the old status line back.** The installer saves `settings.json.bak-<timestamp>` before it changes anything.

## Uninstall

```sh
python3 install.py --uninstall
```

This removes the `statusLine` entry and deletes the script. Nothing else is touched.

## License

No license has been chosen yet.
