"""Render and save review output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


def print_banner(
    console: Console,
    *,
    line_count: int,
    model: str,
    kept: int,
    skipped: int,
    chunks: int,
) -> None:
    skip_note = f" · skipped {skipped} file(s)" if skipped else ""
    chunk_note = f" · {chunks} chunk(s)" if chunks > 1 else ""
    console.print(
        Panel(
            f"Diff: {line_count} lines · {kept} file(s){skip_note}{chunk_note}"
            f" · Model: [cyan]{model}[/cyan]",
            title="AI Code Reviewer",
            border_style="cyan",
        )
    )


def render_review(
    console: Console,
    review: str,
    *,
    output_format: str = "rich",
    output_path: Optional[Path] = None,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    fmt = output_format.lower()
    payload: dict[str, Any] | None = None

    if fmt == "json":
        payload = {
            "review_markdown": review,
            **(meta or {}),
        }
        text = json.dumps(payload, indent=2)
    else:
        text = review

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "json":
            output_path.write_text(text, encoding="utf-8")
        else:
            output_path.write_text(review, encoding="utf-8")
        console.print(f"[green]Wrote[/green] {output_path}")

    console.print()
    if fmt == "json":
        console.print(text)
    elif fmt in ("raw", "markdown"):
        console.print(review)
    else:
        console.print(Markdown(review))
