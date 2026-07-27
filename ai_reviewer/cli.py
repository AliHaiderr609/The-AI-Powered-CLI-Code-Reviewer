"""CLI entrypoint."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console

from ai_reviewer import __version__
from ai_reviewer.config import load_config
from ai_reviewer.filters import chunk_diff, filter_diff
from ai_reviewer.git_diff import GitError, ensure_git_repo, get_diff
from ai_reviewer.llm import merge_chunk_reviews, review_diff
from ai_reviewer.output import print_banner, render_review
from ai_reviewer.severity import exit_code_for, extract_highest_severity

load_dotenv()
console = Console()


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="ai-reviewer")
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
    help="OpenAI model (overrides config / OPENAI_MODEL).",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help="Path to .reviewerrc JSON config.",
)
@click.option(
    "--ignore",
    multiple=True,
    help="Glob pattern to ignore (repeatable). Merged with config defaults.",
)
@click.option(
    "--include",
    multiple=True,
    help="Only include paths matching these globs (repeatable).",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["rich", "markdown", "json", "raw"], case_sensitive=False),
    default=None,
    help="Output format (default: rich).",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Write the review to a file as well as stdout.",
)
@click.option(
    "--fail-on",
    default=None,
    type=click.Choice(
        ["none", "critical", "high", "medium", "low", "info"],
        case_sensitive=False,
    ),
    help="Exit with code 2 if findings meet/exceed this severity (for CI).",
)
@click.option(
    "--max-chunk-lines",
    type=int,
    default=None,
    help="Split large diffs into chunks of this many lines.",
)
@click.option(
    "--raw",
    is_flag=True,
    help="Alias for --format raw.",
)
def main(
    staged: bool,
    commit_ref: Optional[str],
    base: Optional[str],
    model: Optional[str],
    config_path: Optional[Path],
    ignore: tuple[str, ...],
    include: tuple[str, ...],
    output_format: Optional[str],
    output_file: Optional[Path],
    fail_on: Optional[str],
    max_chunk_lines: Optional[int],
    raw: bool,
) -> None:
    """Review git diffs with OpenAI for security issues and refactoring ideas."""
    if sum(bool(x) for x in (staged, commit_ref, base)) > 1:
        console.print(
            "[red]Error:[/red] use only one of --staged, --commit, or --base."
        )
        sys.exit(1)

    try:
        ensure_git_repo()
    except GitError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    try:
        cfg = load_config(config_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        console.print(
            "[red]Error:[/red] OPENAI_API_KEY is not set.\n"
            "Copy .env.example to .env and add your key, or export it in the shell."
        )
        sys.exit(1)

    chosen_model = model or cfg.model
    fmt = "raw" if raw else (output_format or cfg.output_format)
    threshold = fail_on or cfg.fail_on
    chunk_limit = (
        max_chunk_lines if max_chunk_lines is not None else cfg.max_chunk_lines
    )

    ignore_patterns = list(cfg.ignore) + list(ignore)
    include_patterns = list(include) if include else list(cfg.include)

    with console.status("[bold cyan]Collecting git diff..."):
        try:
            diff = get_diff(staged=staged, commit=commit_ref, base=base)
        except GitError as exc:
            console.print(f"[red]Error getting diff:[/red] {exc}")
            sys.exit(1)

    if not diff.strip():
        console.print(
            "[yellow]No changes found.[/yellow] "
            "Make some edits, stage files, or pass --commit / --base."
        )
        sys.exit(0)

    filtered, kept_paths, skipped_paths = filter_diff(
        diff, ignore=ignore_patterns, include=include_patterns or None
    )

    if not filtered.strip():
        console.print(
            "[yellow]All changed files were filtered out.[/yellow] "
            f"Skipped: {', '.join(skipped_paths) or '(none)'}"
        )
        sys.exit(0)

    chunks = chunk_diff(filtered, max_lines=chunk_limit)
    line_count = filtered.count("\n") + 1
    print_banner(
        console,
        line_count=line_count,
        model=chosen_model,
        kept=len(kept_paths),
        skipped=len(skipped_paths),
        chunks=len(chunks),
    )
    if skipped_paths:
        preview = ", ".join(skipped_paths[:8])
        suffix = "…" if len(skipped_paths) > 8 else ""
        console.print(f"[dim]Ignored:[/dim] {preview}{suffix}")

    try:
        reviews: list[str] = []
        for index, chunk in enumerate(chunks):
            label = (
                f"Sending chunk {index + 1}/{len(chunks)} to OpenAI..."
                if len(chunks) > 1
                else "Sending diff to OpenAI..."
            )
            with console.status(f"[bold cyan]{label}"):
                reviews.append(
                    review_diff(
                        chunk,
                        chosen_model,
                        api_key,
                        custom_prompt=cfg.custom_prompt,
                        chunk_index=index,
                        chunk_total=len(chunks),
                    )
                )
        review = merge_chunk_reviews(reviews)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]OpenAI API error:[/red] {exc}")
        sys.exit(1)

    highest = extract_highest_severity(review)
    meta = {
        "model": chosen_model,
        "highest_severity": highest,
        "files_reviewed": kept_paths,
        "files_skipped": skipped_paths,
        "chunks": len(chunks),
    }

    render_review(
        console,
        review,
        output_format=fmt,
        output_path=output_file,
        meta=meta,
    )

    console.print()
    console.print(f"[bold]Highest severity:[/bold] {highest}")

    code = exit_code_for(highest, threshold)
    if code != 0:
        console.print(
            f"[red]Failing:[/red] severity {highest} meets --fail-on={threshold}"
        )
    sys.exit(code)
