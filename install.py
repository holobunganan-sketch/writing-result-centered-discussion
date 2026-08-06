#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

SKILL_NAME = "writing-result-centered-discussion"
EXCLUDE = {"__pycache__", ".pytest_cache", ".discussion-workspace", ".git", ".worktrees", ".superpowers"}


def default_base() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def ignore(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in EXCLUDE or name.endswith(".pyc") or name.endswith(".zip")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the writing-result-centered-discussion Codex Skill")
    parser.add_argument("--target", type=Path, default=None, help="Base skills directory; the skill name is appended")
    parser.add_argument("--force", action="store_true", help="Replace an existing installation")
    args = parser.parse_args()

    source = Path(__file__).resolve().parent
    base = (args.target or default_base()).expanduser().resolve()
    destination = base / SKILL_NAME
    base.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if not args.force:
            raise SystemExit(f"Installation exists: {destination}. Re-run with --force to replace it.")
        shutil.rmtree(destination)

    shutil.copytree(source, destination, ignore=ignore)
    required = destination / "SKILL.md"
    if not required.exists():
        shutil.rmtree(destination, ignore_errors=True)
        raise SystemExit("Installation failed: SKILL.md was not copied")

    print(f"Installed: {destination}")
    print("Restart Codex to refresh skill discovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
