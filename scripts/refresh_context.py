#!/usr/bin/env python3
"""
Refresh project context for the AI assistant by scanning documentation sources
and generating a concise sync summary under .cursor/rules.

Scanned directories:
- _tasks/
- docs/
- claudedocs/

Outputs:
- .cursor/rules/context-state.json   (machine-readable file mtimes)
- .cursor/rules/context-sync.mdc     (human-readable summary for assistants)

Usage:
  python scripts/refresh_context.py

Exit codes:
  0 on success, non-zero on failure.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = REPO_ROOT / ".cursor" / "rules"
STATE_FILE = RULES_DIR / "context-state.json"
SYNC_MDC = RULES_DIR / "context-sync.mdc"

SCAN_DIRS = [REPO_ROOT / d for d in ("_tasks", "docs", "claudedocs")]
VALID_EXTENSIONS = {".md", ".mdx"}


@dataclass(frozen=True)
class FileInfo:
    path: Path
    mtime: float

    @property
    def relpath(self) -> str:
        return str(self.path.relative_to(REPO_ROOT))

    @property
    def mtime_iso(self) -> str:
        return datetime.fromtimestamp(self.mtime, tz=UTC).astimezone().isoformat()


def find_docs_files(directories: Iterable[Path]) -> dict[str, FileInfo]:
    files: dict[str, FileInfo] = {}
    for base in directories:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in VALID_EXTENSIONS:
                try:
                    stat = path.stat()
                except OSError:
                    continue
                info = FileInfo(path=path, mtime=stat.st_mtime)
                files[info.relpath] = info
    return files


def load_previous_state(state_file: Path) -> dict[str, float]:
    if not state_file.exists():
        return {}
    try:
        with state_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        # Only keep string->float mappings
        return {k: float(v) for k, v in data.items() if isinstance(k, str)}
    except Exception:
        return {}


def diff_states(
    prev: dict[str, float], curr: dict[str, FileInfo]
) -> tuple[list[FileInfo], list[str]]:
    added_or_modified: list[FileInfo] = []
    removed: list[str] = []

    for rel, info in curr.items():
        prev_mtime = prev.get(rel)
        if prev_mtime is None or abs(info.mtime - prev_mtime) > 1e-6:
            added_or_modified.append(info)

    for rel in prev.keys():
        if rel not in curr:
            removed.append(rel)

    # Sort deterministically
    added_or_modified.sort(key=lambda i: i.relpath)
    removed.sort()
    return added_or_modified, removed


def write_state(state_file: Path, curr: dict[str, FileInfo]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("w", encoding="utf-8") as f:
        json.dump({rel: info.mtime for rel, info in sorted(curr.items())}, f, indent=2)


def render_sync_mdc(added_or_modified: list[FileInfo], removed: list[str]) -> str:
    now = datetime.now().astimezone().isoformat()
    lines: list[str] = []
    lines.append('# Context Sync Status\n# glob pattern(s) for applicable files: "**/*"\n')
    lines.append(f"**Last Sync**: {now}\n")

    if not added_or_modified and not removed:
        lines.append("本次未檢測到文件變更。模型可使用現有規則檔。\n")
    else:
        if added_or_modified:
            lines.append("## 變更的文件（新增或更新）\n")
            for info in added_or_modified:
                lines.append(f"- {info.relpath}  (modified_at: {info.mtime_iso})\n")
        if removed:
            lines.append("\n## 已刪除的文件\n")
            for rel in removed:
                lines.append(f"- {rel}\n")

        lines.append("\n## 使用指引\n")
        lines.append(
            "- 若此清單非空，請優先參考上述變更的文件與 `_tasks`/`docs` 來源，再更新 `.cursor/rules` 中對應規則檔（如 pagination 或 projects）。\n"
        )
        lines.append("- 任何與上述文件有衝突的舊敘述，應以最新來源文件為準。\n")

    return "".join(lines)


def write_sync_mdc(sync_file: Path, content: str) -> None:
    sync_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_file.open("w", encoding="utf-8") as f:
        f.write(content)


def main() -> int:
    current = find_docs_files(SCAN_DIRS)
    previous = load_previous_state(STATE_FILE)
    changed, removed = diff_states(previous, current)

    # Write state and summary
    write_state(STATE_FILE, current)
    write_sync_mdc(SYNC_MDC, render_sync_mdc(changed, removed))

    # Console summary
    print(
        f"Scanned {len(current)} files under: {', '.join(str(d.relative_to(REPO_ROOT)) for d in SCAN_DIRS)}"
    )
    print(f"Changed: {len(changed)}, Removed: {len(removed)}")
    print(f"Updated: {SYNC_MDC.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
