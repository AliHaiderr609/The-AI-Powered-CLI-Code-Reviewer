"""Git helpers for collecting diffs."""

from __future__ import annotations

import subprocess
import sys
from typing import Optional

from rich.console import Console

console = Console(stderr=True)


class GitError(RuntimeError):
    """Raised when a git command fails."""


def run_git(args: list[str]) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not on PATH.") from exc


def ensure_git_repo() -> None:
    code, _, err = run_git(["rev-parse", "--is-inside-work-tree"])
    if code != 0:
        raise GitError(f"not a git repository.\n{err.strip()}")


def get_diff(
    staged: bool = False,
    commit: Optional[str] = None,
    base: Optional[str] = None,
) -> str:
    """Collect a git diff based on CLI options."""
    if commit:
        code, out, err = run_git(["show", "--pretty=format:", "--patch", commit])
    elif base:
        code, out, err = run_git(["diff", base])
    elif staged:
        code, out, err = run_git(["diff", "--cached"])
    else:
        code, out, err = run_git(["diff"])
        if code == 0 and not out.strip():
            code, out, err = run_git(["diff", "--cached"])

    if code != 0:
        raise GitError(err.strip() or out.strip() or "failed to get diff")

    return out


def die_on_git_error(exc: GitError) -> None:
    console.print(f"[red]Error:[/red] {exc}")
    sys.exit(1)
