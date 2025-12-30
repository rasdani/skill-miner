#!/usr/bin/env python3
"""
Discover Claude Code and Cursor history locations on local or remote machines.
"""

import os
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HistoryLocation:
    """Represents a discovered history location."""
    tool: str  # "claude-code" or "cursor"
    path: Path
    project_name: Optional[str] = None
    session_count: int = 0
    is_remote: bool = False
    host: Optional[str] = None


@dataclass
class DiscoveryResult:
    """Results from history discovery."""
    hostname: str
    claude_code_base: Optional[Path] = None
    cursor_base: Optional[Path] = None
    locations: list = field(default_factory=list)


def get_hostname() -> str:
    """Get the current machine's hostname."""
    import socket
    return socket.gethostname()


def discover_claude_code(home: Path = None) -> list[HistoryLocation]:
    """Discover Claude Code history locations."""
    home = home or Path.home()
    locations = []

    claude_base = home / ".claude"
    if not claude_base.exists():
        return locations

    # Main history index
    history_file = claude_base / "history.jsonl"
    if history_file.exists():
        locations.append(HistoryLocation(
            tool="claude-code",
            path=history_file,
            project_name="_index",
            session_count=sum(1 for _ in open(history_file))
        ))

    # Project-specific histories
    projects_dir = claude_base / "projects"
    if projects_dir.exists():
        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir() and not project_dir.name.startswith('.'):
                # Decode project name from directory name
                project_name = project_dir.name.replace('-', '/')
                if project_name.startswith('/'):
                    project_name = project_name[1:]

                session_files = list(project_dir.glob("*.jsonl"))
                if session_files:
                    locations.append(HistoryLocation(
                        tool="claude-code",
                        path=project_dir,
                        project_name=project_name,
                        session_count=len(session_files)
                    ))

    return locations


def discover_cursor(home: Path = None) -> list[HistoryLocation]:
    """Discover Cursor history locations."""
    home = home or Path.home()
    locations = []

    # Check multiple possible Cursor locations
    cursor_paths = [
        home / ".config" / "Cursor" / "User" / "workspaceStorage",  # Linux desktop
        home / ".cursor-server" / "data" / "User" / "workspaceStorage",  # Linux server/remote
        home / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage",  # macOS
    ]

    for ws_path in cursor_paths:
        if ws_path.exists():
            for workspace_dir in ws_path.iterdir():
                if workspace_dir.is_dir():
                    # Look for state.vscdb or other chat data
                    state_db = workspace_dir / "state.vscdb"
                    if state_db.exists():
                        locations.append(HistoryLocation(
                            tool="cursor",
                            path=workspace_dir,
                            project_name=workspace_dir.name[:12] + "...",  # Hash prefix
                            session_count=1
                        ))
                    else:
                        # Still track the workspace even without state.vscdb
                        locations.append(HistoryLocation(
                            tool="cursor",
                            path=workspace_dir,
                            project_name=workspace_dir.name[:12] + "...",
                            session_count=0
                        ))

    # Also check for Cursor's file history
    history_paths = [
        home / ".cursor-server" / "data" / "User" / "History",
        home / ".config" / "Cursor" / "User" / "History",
    ]

    for hist_path in history_paths:
        if hist_path.exists():
            history_dirs = [d for d in hist_path.iterdir() if d.is_dir()]
            if history_dirs:
                locations.append(HistoryLocation(
                    tool="cursor",
                    path=hist_path,
                    project_name="_file_history",
                    session_count=len(history_dirs)
                ))

    return locations


def discover_all(home: Path = None) -> DiscoveryResult:
    """Discover all history locations."""
    home = home or Path.home()
    hostname = get_hostname()

    claude_locations = discover_claude_code(home)
    cursor_locations = discover_cursor(home)

    result = DiscoveryResult(
        hostname=hostname,
        claude_code_base=home / ".claude" if (home / ".claude").exists() else None,
        cursor_base=None,
        locations=claude_locations + cursor_locations
    )

    # Set cursor base if found
    for loc in cursor_locations:
        if loc.path.exists():
            # Find the base cursor directory
            path_str = str(loc.path)
            if ".cursor-server" in path_str:
                result.cursor_base = home / ".cursor-server"
            elif ".config/Cursor" in path_str:
                result.cursor_base = home / ".config" / "Cursor"
            break

    return result


def print_discovery_report(result: DiscoveryResult):
    """Print a human-readable discovery report."""
    print(f"\n{'='*60}")
    print(f"History Discovery Report - {result.hostname}")
    print(f"{'='*60}\n")

    claude_locs = [l for l in result.locations if l.tool == "claude-code"]
    cursor_locs = [l for l in result.locations if l.tool == "cursor"]

    if result.claude_code_base:
        print(f"Claude Code Base: {result.claude_code_base}")
        print(f"  Found {len(claude_locs)} location(s):")
        for loc in claude_locs:
            print(f"    - {loc.project_name}: {loc.session_count} session(s)")
    else:
        print("Claude Code: Not found")

    print()

    if result.cursor_base:
        print(f"Cursor Base: {result.cursor_base}")
        print(f"  Found {len(cursor_locs)} location(s):")
        for loc in cursor_locs:
            print(f"    - {loc.project_name}: {loc.session_count} session(s)")
    else:
        print("Cursor: Not found")

    print()


def to_json(result: DiscoveryResult) -> dict:
    """Convert discovery result to JSON-serializable dict."""
    return {
        "hostname": result.hostname,
        "claude_code_base": str(result.claude_code_base) if result.claude_code_base else None,
        "cursor_base": str(result.cursor_base) if result.cursor_base else None,
        "locations": [
            {
                "tool": loc.tool,
                "path": str(loc.path),
                "project_name": loc.project_name,
                "session_count": loc.session_count,
                "is_remote": loc.is_remote,
                "host": loc.host
            }
            for loc in result.locations
        ]
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Discover Claude Code and Cursor histories")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--home", type=Path, help="Override home directory")
    args = parser.parse_args()

    result = discover_all(args.home)

    if args.json:
        print(json.dumps(to_json(result), indent=2))
    else:
        print_discovery_report(result)
