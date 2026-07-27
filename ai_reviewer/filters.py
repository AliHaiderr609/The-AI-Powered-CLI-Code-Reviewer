"""Filter and split unified diffs by path patterns."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass

FILE_HEADER_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")


@dataclass
class DiffFile:
    path: str
    content: str


def parse_diff_files(diff: str) -> list[DiffFile]:
    """Split a unified diff into per-file chunks."""
    if not diff.strip():
        return []

    lines = diff.splitlines(keepends=True)
    files: list[DiffFile] = []
    current_path: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_path, current_lines
        if current_path is not None and current_lines:
            files.append(DiffFile(path=current_path, content="".join(current_lines)))
        current_path = None
        current_lines = []

    for line in lines:
        match = FILE_HEADER_RE.match(line.rstrip("\n"))
        if match:
            flush()
            current_path = match.group(2) or match.group(1)
            current_lines = [line]
        elif current_path is not None:
            current_lines.append(line)
        else:
            # Preamble before first file header — keep as synthetic chunk
            if not files and not current_lines:
                current_path = "(preamble)"
            if current_path is not None:
                current_lines.append(line)

    flush()
    return files


def _matches(path: str, patterns: list[str]) -> bool:
    name = path.split("/")[-1]
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(name, pattern):
            return True
        # Support ** style loosely via fnmatch on full path
        if "**" in pattern and fnmatch.fnmatch(path, pattern):
            return True
    return False


def filter_diff(
    diff: str,
    ignore: list[str] | None = None,
    include: list[str] | None = None,
) -> tuple[str, list[str], list[str]]:
    """
    Filter a unified diff by ignore/include glob patterns.

    Returns (filtered_diff, kept_paths, skipped_paths).
    """
    ignore = ignore or []
    include = include or []
    files = parse_diff_files(diff)
    if not files:
        return diff, [], []

    kept: list[DiffFile] = []
    skipped: list[str] = []

    for item in files:
        if item.path == "(preamble)":
            kept.append(item)
            continue
        if ignore and _matches(item.path, ignore):
            skipped.append(item.path)
            continue
        if include and not _matches(item.path, include):
            skipped.append(item.path)
            continue
        kept.append(item)

    filtered = "".join(f.content for f in kept)
    kept_paths = [f.path for f in kept if f.path != "(preamble)"]
    return filtered, kept_paths, skipped


def chunk_diff(diff: str, max_lines: int = 400) -> list[str]:
    """
    Split a diff into chunks that fit under max_lines.

    Prefers whole-file boundaries; splits a single large file if needed.
    """
    if max_lines <= 0:
        return [diff] if diff.strip() else []

    files = parse_diff_files(diff)
    if not files:
        return [diff] if diff.strip() else []

    chunks: list[str] = []
    current: list[str] = []
    current_lines = 0

    def flush() -> None:
        nonlocal current, current_lines
        if current:
            chunks.append("".join(current))
        current = []
        current_lines = 0

    for item in files:
        file_lines = item.content.count("\n") + (0 if item.content.endswith("\n") else 1)
        if file_lines > max_lines:
            flush()
            # Hard-split oversized file
            lines = item.content.splitlines(keepends=True)
            for i in range(0, len(lines), max_lines):
                piece = "".join(lines[i : i + max_lines])
                header = (
                    f"# Partial diff for {item.path} "
                    f"(lines {i + 1}-{min(i + max_lines, len(lines))})\n"
                )
                chunks.append(header + piece)
            continue

        if current_lines and current_lines + file_lines > max_lines:
            flush()
        current.append(item.content)
        current_lines += file_lines

    flush()
    return chunks
