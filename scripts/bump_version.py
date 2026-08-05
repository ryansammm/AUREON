"""Release tooling: bump AUREON's version everywhere.

The single source of truth is the root ``VERSION`` file. This script
updates it (SemVer), mirrors the number into ``web/frontend/package.json``
so the whole app ships one version, and can tag the release.

Releases are cut from the ``stable`` branch: ``--tag`` refuses to run on
any other branch so release tags always point at stable.

Usage:
    git checkout stable
    python scripts/bump_version.py --patch              # 0.1.0 -> 0.1.1
    python scripts/bump_version.py --minor              # 0.1.0 -> 0.2.0
    python scripts/bump_version.py --major              # 0.1.0 -> 1.0.0
    python scripts/bump_version.py --set 0.3.0          # explicit version
    python scripts/bump_version.py --patch --tag        # bump + `git tag v0.1.1`
    python scripts/bump_version.py --patch --dry-run    # preview only
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
PACKAGE_JSON = ROOT / "web" / "frontend" / "package.json"
RELEASE_BRANCH = "stable"

SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def current() -> str:
    """Read the current version from the VERSION file."""
    try:
        text = VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SystemExit(f"error: could not read {VERSION_FILE.name}: {exc}")
    return text.splitlines()[0].strip()


def next_version(cur: str, part: str) -> str:
    """SemVer bump: major/minor/patch, resetting lower segments to 0."""
    major, minor, patch = (int(p) for p in cur.split(".")[:3])
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def write(new: str) -> None:
    """Write the new version to VERSION and mirror it into package.json."""
    VERSION_FILE.write_text(new + "\n", encoding="utf-8")
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    data["version"] = new
    PACKAGE_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"VERSION -> {new}")
    print(f"web/frontend/package.json -> version {new}")


def git_tag(version: str) -> None:
    tag = f"v{version}"
    subprocess.run(["git", "tag", tag], check=True, cwd=ROOT)
    print(f"git tag -> {tag}")


def current_branch() -> str:
    """Return the current git branch ('' when in detached HEAD)."""
    proc = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="bump_version",
        description="Bump AUREON's version (root VERSION file + package.json).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--major", action="store_true",
                       help="increment major: 0.1.0 -> 1.0.0")
    group.add_argument("--minor", action="store_true",
                       help="increment minor: 0.1.0 -> 0.2.0")
    group.add_argument("--patch", action="store_true",
                       help="increment patch: 0.1.0 -> 0.1.1")
    group.add_argument("--set", metavar="X.Y.Z",
                       help="set an explicit SemVer version")
    parser.add_argument("--tag", action="store_true",
                        help="create a git tag v<version> after bumping")
    parser.add_argument("--branch", default=RELEASE_BRANCH,
                        help=f"branch release tags must be created on "
                             f"(default: {RELEASE_BRANCH})")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would change without writing anything")
    args = parser.parse_args(argv)

    cur = current()
    if not SEMVER.match(cur):
        parser.error(f"current version {cur!r} in VERSION is not valid SemVer")

    new = args.set if args.set else next_version(
        cur, "major" if args.major else "minor" if args.minor else "patch"
    )
    if not SEMVER.match(new):
        parser.error(f"version {new!r} is not valid SemVer")

    print(f"{cur} -> {new}" + (f" (tag v{new} on {args.branch})" if args.tag else ""))
    if args.dry_run:
        return 0

    if args.tag and current_branch() != args.branch:
        print(
            f"error: releases must be tagged from '{args.branch}', "
            f"current branch is '{current_branch()}'",
            file=sys.stderr,
        )
        return 1

    write(new)
    if args.tag:
        git_tag(new)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
