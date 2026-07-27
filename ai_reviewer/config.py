"""Project and environment configuration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Optional

DEFAULT_IGNORE = [
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.svg",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.ico",
    "*.pdf",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
]

CONFIG_FILENAMES = (".reviewerrc", ".reviewerrc.json", "reviewer.json")


@dataclass
class ReviewerConfig:
    model: str = "gpt-4o-mini"
    ignore: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE))
    include: list[str] = field(default_factory=list)
    max_chunk_lines: int = 400
    fail_on: str = "critical"  # none | critical | high | medium | low
    custom_prompt: Optional[str] = None
    output_format: str = "rich"  # rich | markdown | json | raw

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewerConfig":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        cfg = cls()
        for key, value in filtered.items():
            setattr(cfg, key, value)
        # Merge ignore patterns: defaults + user extras unless replace_ignore
        if "ignore" in data and not data.get("replace_ignore"):
            merged = list(DEFAULT_IGNORE)
            for pattern in data["ignore"]:
                if pattern not in merged:
                    merged.append(pattern)
            cfg.ignore = merged
        return cfg


def find_config_path(start: Optional[Path] = None) -> Optional[Path]:
    directory = (start or Path.cwd()).resolve()
    for path in [directory, *directory.parents]:
        for name in CONFIG_FILENAMES:
            candidate = path / name
            if candidate.is_file():
                return candidate
        if (path / ".git").exists():
            break
    return None


def load_config(path: Optional[Path] = None) -> ReviewerConfig:
    config_path = path or find_config_path()
    if config_path is None:
        return ReviewerConfig(model=os.getenv("OPENAI_MODEL") or "gpt-4o-mini")

    text = config_path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Config {config_path} must be a JSON object")
    cfg = ReviewerConfig.from_dict(data)
    if os.getenv("OPENAI_MODEL") and "model" not in data:
        cfg.model = os.getenv("OPENAI_MODEL") or cfg.model
    return cfg
