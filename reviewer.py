#!/usr/bin/env python3
"""AI-powered CLI code reviewer: analyze git diffs for security and refactoring."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

import click
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

load_dotenv()

console = Console()

SYSTEM_PROMPT = """You are an expert security engineer and software architect.
Review the provided git diff carefully.

Focus on:
1. Security vulnerabilities (injection, auth flaws, secrets leakage, insecure crypto, etc.)
2. Concrete refactoring steps to improve clarity, maintainability, and safety
3. Bugs or edge cases introduced by the change

Respond in clear Markdown with these sections:
## Security findings
## Refactoring steps
## Summary

Be specific: cite file paths and approximate line context from the diff when possible.
If there are no issues in a section, say so briefly. Prefer actionable advice over generic tips.
"""


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
    except FileNotFoundError:
        console.print("[red]Error:[/red] git is not installed or not on PATH.")
        sys.exit(1)


def ensure_git_repo() -> None:
    code, _, err = run_git(["rev-parse", "--is-inside-work-tree"])
    if code != 0:
        console.print(f"[red]Error:[/red] not a git repository.\n{err.strip()}")
        sys.exit(1)


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
        # Unstaged working tree changes; fall back to staged if empty
        code, out, err = run_git(["diff"])
        if code == 0 and not out.strip():
            code, out, err = run_git(["diff", "--cached"])

    if code != 0:
        console.print(f"[red]Error getting diff:[/red] {err.strip() or out.strip()}")
        sys.exit(1)

    return out


def review_diff(diff: str, model: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Please review the following git diff for security "
                    "vulnerabilities and suggest refactoring steps:\n\n"
                    f"```diff\n{diff}\n```"
                ),
            },
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content
    return content or "(No response from model.)"


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--staged",
    is_flag=True,
    help="Review only staged changes (git diff --cached).",
)
@click.option(
    "--commit",
    "commit_ref",
    default=None,
    metavar="REF",
    help="Review a specific commit (e.g. HEAD or abc1234).",
)
@click.option(
    "--base",
    default=None,
    metavar="REF",
    help="Diff against a base ref (e.g. main or origin/main).",
)
@click.option(
    "--model",
    default=None,
    help="OpenAI model (default: OPENAI_MODEL or gpt-4o-mini).",
)
@click.option(
    "--raw",
    is_flag=True,
    help="Print plain text instead of rich Markdown.",
)
def main(
    staged: bool,
    commit_ref: Optional[str],
    base: Optional[str],
    model: Optional[str],
    raw: bool,
) -> None:
    """Review git diffs with OpenAI for security issues and refactoring ideas."""
    if sum(bool(x) for x in (staged, commit_ref, base)) > 1:
        console.print(
            "[red]Error:[/red] use only one of --staged, --commit, or --base."
        )
        sys.exit(1)

    ensure_git_repo()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print(
            "[red]Error:[/red] OPENAI_API_KEY is not set.\n"
            "Copy .env.example to .env and add your key, or export it in the shell."
        )
        sys.exit(1)

    chosen_model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    with console.status("[bold cyan]Collecting git diff..."):
        diff = get_diff(staged=staged, commit=commit_ref, base=base)

    if not diff.strip():
        console.print(
            "[yellow]No changes found.[/yellow] "
            "Make some edits, stage files, or pass --commit / --base."
        )
        sys.exit(0)

    line_count = diff.count("\n") + 1
    console.print(
        Panel(
            f"Diff size: {line_count} lines · Model: [cyan]{chosen_model}[/cyan]",
            title="AI Code Reviewer",
            border_style="cyan",
        )
    )

    try:
        with console.status("[bold cyan]Sending diff to OpenAI..."):
            review = review_diff(diff, chosen_model, api_key)
    except Exception as exc:  # noqa: BLE001 — surface API errors cleanly
        console.print(f"[red]OpenAI API error:[/red] {exc}")
        sys.exit(1)

    console.print()
    if raw:
        console.print(review)
    else:
        console.print(Markdown(review))


if __name__ == "__main__":
    main()
