---
name: history-sync
description: Discover and consolidate Claude Code and Cursor AI history/session data from local and remote machines. Use when the user wants to find, backup, or aggregate their AI coding assistant histories, extract conversation data from multiple development machines, or create a unified view of Claude Code sessions and Cursor chats across hosts.
---

# History Sync

Discover and consolidate Claude Code and Cursor AI conversation histories from local and remote development machines into a unified directory structure.

## History Locations

### Claude Code
- **Base**: `~/.claude/`
- **Index**: `~/.claude/history.jsonl` (session metadata)
- **Sessions**: `~/.claude/projects/<encoded-path>/*.jsonl` (full conversations)

### Cursor
- **Linux desktop**: `~/.config/Cursor/User/workspaceStorage/`
- **Linux server/remote**: `~/.cursor-server/data/User/workspaceStorage/`
- **macOS**: `~/Library/Application Support/Cursor/User/workspaceStorage/`
- **Session data**: `state.vscdb` (SQLite) with keys `aiService.prompts`, `workbench.panel.aichat.view.aichat.chatdata`

## Quick Start

### Discover Local Histories

```bash
python3 scripts/discover.py
```

Output shows found histories with session counts. Use `--json` for machine-readable output.

### Consolidate Local Histories

```bash
python3 scripts/consolidate.py --output ~/.history-sync
```

Creates:
```
~/.history-sync/
├── .gitignore
└── <hostname>/
    ├── claude-code -> ~/.claude (symlink)
    └── cursor -> ~/.cursor-server (symlink)
```

### Pull Remote Histories

```bash
python3 scripts/pull_remote.py user@remote-host --output ~/.history-sync
```

Syncs remote histories via rsync. Multiple hosts: `python3 scripts/pull_remote.py host1 host2 host3`

Options:
- `--dry-run`: Preview without syncing
- `--port PORT`: SSH port
- `--identity FILE`: SSH key
- `--no-claude` / `--no-cursor`: Skip specific tool

## Workflow: Full Consolidation

1. **Discover local**: `python3 scripts/discover.py`
2. **Create base**: `python3 scripts/consolidate.py -o ~/.history-sync`
3. **Pull remotes**: `python3 scripts/pull_remote.py user@dev1 user@dev2 -o ~/.history-sync`
4. **View all**: `python3 scripts/consolidate.py -l -o ~/.history-sync`

Result:
```
~/.history-sync/
├── .gitignore
├── local-hostname/
│   ├── claude-code -> ~/.claude (symlink)
│   └── cursor -> ~/.cursor-server (symlink)
├── dev-server-1/
│   ├── claude-code/ (copied files)
│   └── cursor/
└── dev-server-2/
    ├── claude-code/
    └── cursor/
```

## Scripts

| Script | Purpose |
|--------|---------|
| `discover.py` | Find Claude Code and Cursor histories on current machine |
| `consolidate.py` | Create unified folder with symlinks for local histories |
| `pull_remote.py` | Sync histories from remote machines via SSH/rsync |

## Notes

- Local histories use symlinks (no duplication)
- Remote histories are actual copies (rsync'd)
- `.gitignore` auto-generated to exclude remote data from version control
- Cursor server mode stores minimal chat data locally (chat history on client)
