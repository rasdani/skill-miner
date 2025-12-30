#!/usr/bin/env python3
"""
Pull Claude Code and Cursor histories from remote machines.

Uses rsync over SSH to efficiently sync history directories.
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class RemoteHost:
    """Configuration for a remote host."""
    hostname: str
    user: str = ""
    ssh_host: str = ""  # user@host or just host
    port: int = 22
    identity_file: Optional[Path] = None

    def __post_init__(self):
        if not self.ssh_host:
            self.ssh_host = f"{self.user}@{self.hostname}" if self.user else self.hostname


def run_ssh_command(host: RemoteHost, command: str) -> tuple[int, str, str]:
    """Run a command on a remote host via SSH."""
    ssh_args = ["ssh"]

    if host.port != 22:
        ssh_args.extend(["-p", str(host.port)])

    if host.identity_file:
        ssh_args.extend(["-i", str(host.identity_file)])

    ssh_args.extend([host.ssh_host, command])

    result = subprocess.run(
        ssh_args,
        capture_output=True,
        text=True
    )

    return result.returncode, result.stdout, result.stderr


def rsync_remote_dir(
    host: RemoteHost,
    remote_path: str,
    local_path: Path,
    dry_run: bool = False
) -> bool:
    """
    Rsync a directory from remote host to local.

    Returns True if successful.
    """
    local_path.mkdir(parents=True, exist_ok=True)

    rsync_args = [
        "rsync",
        "-avz",  # archive, verbose, compress
        "--progress",
        "--delete",  # Remove files that don't exist on remote
    ]

    if dry_run:
        rsync_args.append("--dry-run")

    if host.port != 22:
        rsync_args.extend(["-e", f"ssh -p {host.port}"])

    if host.identity_file:
        rsync_args.extend(["-e", f"ssh -i {host.identity_file}"])

    # Remote source
    remote_src = f"{host.ssh_host}:{remote_path}"
    rsync_args.append(remote_src)

    # Local destination
    rsync_args.append(str(local_path) + "/")

    print(f"  Syncing: {remote_src} -> {local_path}")

    result = subprocess.run(rsync_args)

    return result.returncode == 0


def discover_remote_histories(host: RemoteHost) -> dict:
    """
    Discover what history directories exist on a remote host.

    Returns dict with 'claude_code' and 'cursor' keys containing paths if found.
    """
    discoveries = {
        "claude_code": None,
        "cursor": None
    }

    # Check for Claude Code
    claude_paths = [
        "~/.claude"
    ]
    for path in claude_paths:
        ret, stdout, stderr = run_ssh_command(host, f"test -d {path} && echo exists")
        if "exists" in stdout:
            discoveries["claude_code"] = path
            break

    # Check for Cursor
    cursor_paths = [
        "~/.cursor-server",
        "~/.config/Cursor",
        "~/.cursor"
    ]
    for path in cursor_paths:
        ret, stdout, stderr = run_ssh_command(host, f"test -d {path} && echo exists")
        if "exists" in stdout:
            discoveries["cursor"] = path
            break

    return discoveries


def pull_from_remote(
    host: RemoteHost,
    consolidated_dir: Path,
    claude_code: bool = True,
    cursor: bool = True,
    dry_run: bool = False
) -> bool:
    """
    Pull histories from a remote host.

    Creates directory structure:
        consolidated_dir/
        └── hostname/
            ├── claude-code/
            └── cursor/
    """
    print(f"\nPulling from {host.ssh_host}")
    print("-" * 50)

    # First discover what exists
    print("Discovering remote histories...")
    discoveries = discover_remote_histories(host)

    if not discoveries["claude_code"] and not discoveries["cursor"]:
        print(f"  No histories found on {host.hostname}")
        return False

    host_dir = consolidated_dir / host.hostname
    host_dir.mkdir(parents=True, exist_ok=True)

    success = True

    # Pull Claude Code
    if claude_code and discoveries["claude_code"]:
        print(f"\nClaude Code found at: {discoveries['claude_code']}")
        local_claude = host_dir / "claude-code"

        if not rsync_remote_dir(host, discoveries["claude_code"] + "/", local_claude, dry_run):
            print(f"  Failed to sync Claude Code")
            success = False
    elif claude_code:
        print("\nClaude Code: Not found on remote")

    # Pull Cursor
    if cursor and discoveries["cursor"]:
        print(f"\nCursor found at: {discoveries['cursor']}")
        local_cursor = host_dir / "cursor"

        if not rsync_remote_dir(host, discoveries["cursor"] + "/", local_cursor, dry_run):
            print(f"  Failed to sync Cursor")
            success = False
    elif cursor:
        print("\nCursor: Not found on remote")

    return success


def pull_from_multiple(
    hosts: list[RemoteHost],
    consolidated_dir: Path,
    dry_run: bool = False
):
    """Pull from multiple remote hosts."""
    print(f"\nPulling histories from {len(hosts)} host(s)")
    print("=" * 60)

    results = {}
    for host in hosts:
        try:
            results[host.hostname] = pull_from_remote(
                host,
                consolidated_dir,
                dry_run=dry_run
            )
        except Exception as e:
            print(f"\nError pulling from {host.hostname}: {e}")
            results[host.hostname] = False

    print("\n" + "=" * 60)
    print("Summary:")
    for hostname, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {hostname}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Pull histories from remote machines"
    )
    parser.add_argument(
        "hosts",
        nargs="+",
        help="Remote hosts to pull from (user@host or just host)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path.home() / ".history-sync",
        help="Output directory for consolidated histories"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=22,
        help="SSH port"
    )
    parser.add_argument(
        "--identity", "-i",
        type=Path,
        help="SSH identity file"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be synced without actually syncing"
    )
    parser.add_argument(
        "--no-claude",
        action="store_true",
        help="Skip Claude Code histories"
    )
    parser.add_argument(
        "--no-cursor",
        action="store_true",
        help="Skip Cursor histories"
    )
    args = parser.parse_args()

    # Parse hosts
    hosts = []
    for host_str in args.hosts:
        if "@" in host_str:
            user, hostname = host_str.split("@", 1)
        else:
            user = ""
            hostname = host_str

        hosts.append(RemoteHost(
            hostname=hostname,
            user=user,
            port=args.port,
            identity_file=args.identity
        ))

    if len(hosts) == 1:
        pull_from_remote(
            hosts[0],
            args.output,
            claude_code=not args.no_claude,
            cursor=not args.no_cursor,
            dry_run=args.dry_run
        )
    else:
        pull_from_multiple(hosts, args.output, args.dry_run)
