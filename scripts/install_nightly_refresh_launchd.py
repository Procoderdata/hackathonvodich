#!/usr/bin/env python3
"""Install a nightly launchd job to refresh orbital catalog data."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

PLIST_TEMPLATE = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
  <key>Label</key>
  <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{python_exec}</string>
    <string>{refresh_script}</string>
    <string>--output</string>
    <string>{output_csv}</string>
    <string>--meta</string>
    <string>{meta_json}</string>
    <string>--limit</string>
    <string>{limit}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>{hour}</integer>
    <key>Minute</key>
    <integer>{minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>{stdout_log}</string>
  <key>StandardErrorPath</key>
  <string>{stderr_log}</string>
</dict>
</plist>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install nightly orbital refresh on macOS launchd")
    parser.add_argument("--hour", type=int, default=2, help="Local hour (0-23)")
    parser.add_argument("--minute", type=int, default=15, help="Local minute (0-59)")
    parser.add_argument("--limit", type=int, default=1500, help="Row cap passed to refresh script")
    parser.add_argument("--label", type=str, default="com.atlas.orbital.refresh", help="launchd label")
    parser.add_argument(
        "--plist",
        type=Path,
        default=Path.home() / "Library/LaunchAgents/com.atlas.orbital.refresh.plist",
        help="Target launchd plist path",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path",
    )
    return parser.parse_args()


def install_job(args: argparse.Namespace) -> None:
    project_root = args.project_root.resolve()
    refresh_script = (project_root / "scripts/refresh_orbital_catalog.py").resolve()
    output_csv = (project_root / "data/orbital_elements.csv").resolve()
    meta_json = (project_root / "data/orbital_elements.meta.json").resolve()
    logs_dir = (project_root / "logs").resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    if not refresh_script.exists():
        raise FileNotFoundError(f"Refresh script not found: {refresh_script}")

    plist_path = args.plist.expanduser().resolve()
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    plist_content = PLIST_TEMPLATE.format(
        label=args.label,
        python_exec=Path(sys.executable).resolve(),
        refresh_script=refresh_script,
        output_csv=output_csv,
        meta_json=meta_json,
        limit=args.limit,
        hour=args.hour,
        minute=args.minute,
        stdout_log=(logs_dir / "orbital_refresh.out.log"),
        stderr_log=(logs_dir / "orbital_refresh.err.log"),
    )
    plist_path.write_text(plist_content, encoding="utf-8")

    subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
    subprocess.run(["launchctl", "load", str(plist_path)], check=True)

    print(f"Installed launchd job: {plist_path}")
    print(f"Schedule: daily at {args.hour:02d}:{args.minute:02d} local time")


def main() -> None:
    args = parse_args()
    install_job(args)


if __name__ == "__main__":
    main()
