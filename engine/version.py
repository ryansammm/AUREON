"""AUREON version information.

The single source of truth is the ``VERSION`` file in the repo root.
``get_version_info()`` merges it with git build metadata so the CLI, the
API and the UI all report the same number plus provenance (commit hash,
build time, dirty-tree flag).
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
FALLBACK_VERSION = "0.0.0"


def _load_version() -> str:
    try:
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return FALLBACK_VERSION
    return text.splitlines()[0].strip() or FALLBACK_VERSION


def _git(*args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout.strip()


def _git_dirty() -> bool:
    return bool(_git("status", "--porcelain"))


@dataclass(frozen=True)
class VersionInfo:
    name: str
    version: str
    commit: str
    dirty: bool
    build_time: str
    python: str

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "commit": self.commit,
            "dirty": self.dirty,
            "build_time": self.build_time,
            "python": self.python,
        }


@lru_cache(maxsize=1)
def get_version_info() -> VersionInfo:
    from datetime import datetime, timezone

    return VersionInfo(
        name="aureon",
        version=_load_version(),
        commit=_git("rev-parse", "--short", "HEAD") or "",
        dirty=_git_dirty(),
        build_time=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        python=sys.version.split()[0],
    )


__version__ = get_version_info().version
