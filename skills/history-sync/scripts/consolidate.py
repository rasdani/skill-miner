#!/usr/bin/env python3
"""
Consolidate Claude Code and Cursor histories into a unified folder structure.

Creates a directory structure like:
    consolidated/
    ├── .gitignore
    ├── local-hostname/
    │   ├── claude-code -> ~/.claude (symlink)
    │   └── cursor -> ~/.cursor-server or ~/.config/Cursor (symlink)
    └── remote-hostname/
        ├── claude-code/  (actual files pulled from remote)
        └── cursor/       (actual files pulled from remote)
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from discover import discover_all, DiscoveryResult, get_hostname


def ensure_gitignore(consolidated_dir: Path):
    """Ensure the consolidated directory has a .gitignore that ignores remote data."""
    gitignore_path = consolidated_dir / ".gitignore"

    gitignore_content = """\
# Ignore remote history data (actual files, not symlinks)
# Keep symlinks for local histories

# Ignore all remote host directories (they contain actual data)
*/claude-code/
*/cursor/

# But don't ignore the symlinks (they're just pointers)
!*/claude-code
!*/cursor

# Ignore any pulled archives
*.tar.gz
*.zip

# Common patterns to ignore
*.pyc
__pycache__/
.DS_Store
"""

    gitignore_path.write_text(gitignore_content)
    print(f"Created .gitignore at {gitignore_path}")


def consolidate_local(
    consolidated_dir: Path,
    discovery: DiscoveryResult,
    force: bool = False
) -> Path:
    """
    Create symlinks to local history directories.

    Returns the path to the local host directory.
    """
    host_dir = consolidated_dir / discovery.hostname
    host_dir.mkdir(parents=True, exist_ok=True)

    # Create symlink for Claude Code
    if discovery.claude_code_base:
        claude_link = host_dir / "claude-code"
        if claude_link.exists() or claude_link.is_symlink():
            if force:
                claude_link.unlink()
            else:
                print(f"  Skipping {claude_link} (already exists)")

        if not claude_link.exists() and not claude_link.is_symlink():
            claude_link.symlink_to(discovery.claude_code_base)
            print(f"  Created symlink: {claude_link} -> {discovery.claude_code_base}")

    # Create symlink for Cursor
    if discovery.cursor_base:
        cursor_link = host_dir / "cursor"
        if cursor_link.exists() or cursor_link.is_symlink():
            if force:
                cursor_link.unlink()
            else:
                print(f"  Skipping {cursor_link} (already exists)")

        if not cursor_link.exists() and not cursor_link.is_symlink():
            cursor_link.symlink_to(discovery.cursor_base)
            print(f"  Created symlink: {cursor_link} -> {discovery.cursor_base}")

    return host_dir


def setup_remote_dir(consolidated_dir: Path, hostname: str) -> Path:
    """
    Create directory structure for remote host data.

    Returns the path to the remote host directory.
    """
    host_dir = consolidated_dir / hostname
    host_dir.mkdir(parents=True, exist_ok=True)

    (host_dir / "claude-code").mkdir(exist_ok=True)
    (host_dir / "cursor").mkdir(exist_ok=True)

    return host_dir


def consolidate(
    output_dir: Path = None,
    force: bool = False
) -> Path:
    """
    Main consolidation function.

    Creates the consolidated directory structure with symlinks for local histories.
    Returns the path to the consolidated directory.
    """
    output_dir = output_dir or Path.home() / ".history-sync"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nConsolidating histories to: {output_dir}")
    print("-" * 50)

    # Ensure .gitignore exists
    ensure_gitignore(output_dir)

    # Discover local histories
    discovery = discover_all()

    print(f"\nLocal host: {discovery.hostname}")
    consolidate_local(output_dir, discovery, force)

    print(f"\nConsolidation complete!")
    print(f"View histories at: {output_dir}")

    return output_dir


def list_consolidated(consolidated_dir: Path = None):
    """List all consolidated histories."""
    consolidated_dir = consolidated_dir or Path.home() / ".history-sync"

    if not consolidated_dir.exists():
        print("No consolidated histories found.")
        print(f"Run: consolidate.py to create at {consolidated_dir}")
        return

    print(f"\nConsolidated Histories: {consolidated_dir}")
    print("=" * 60)

    for host_dir in sorted(consolidated_dir.iterdir()):
        if host_dir.is_dir():
            print(f"\n{host_dir.name}/")

            for tool_dir in sorted(host_dir.iterdir()):
                if tool_dir.is_symlink():
                    target = tool_dir.resolve()
                    print(f"  {tool_dir.name} -> {target} (symlink)")
                elif tool_dir.is_dir():
                    # Count files for remote directories
                    file_count = sum(1 for _ in tool_dir.rglob("*") if _.is_file())
                    print(f"  {tool_dir.name}/ ({file_count} files)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Consolidate Claude Code and Cursor histories"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path.home() / ".history-sync",
        help="Output directory for consolidated histories"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force overwrite existing symlinks"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List consolidated histories"
    )
    args = parser.parse_args()

    if args.list:
        list_consolidated(args.output)
    else:
        consolidate(args.output, args.force)
