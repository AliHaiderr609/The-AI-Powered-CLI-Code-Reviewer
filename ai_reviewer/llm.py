"""OpenAI review client."""

from __future__ import annotations

from typing import Optional

from openai import OpenAI

DEFAULT_SYSTEM_PROMPT = """You are an expert security engineer and software architect.
Review the provided git diff carefully.

Focus on:
1. Security vulnerabilities (injection, auth flaws, secrets leakage, insecure crypto, etc.)
2. Concrete refactoring steps to improve clarity, maintainability, and safety
3. Bugs or edge cases introduced by the change

Respond in clear Markdown with these sections EXACTLY:

## Security findings
For each finding use this format:
- **[SEVERITY]** `path`: description
  Severity must be one of: CRITICAL, HIGH, MEDIUM, LOW, INFO

## Refactoring steps
Numbered, actionable steps.

## Summary
2-4 sentences. End with a line: `Highest severity: CRITICAL|HIGH|MEDIUM|LOW|INFO|NONE`

Be specific: cite file paths from the diff when possible.
If there are no issues in a section, say so briefly.
Prefer actionable advice over generic tips.
"""


def build_system_prompt(custom_prompt: Optional[str] = None) -> str:
    if not custom_prompt:
        return DEFAULT_SYSTEM_PROMPT
    return (
        f"{DEFAULT_SYSTEM_PROMPT}\n\n"
        f"## Project-specific guidance\n{custom_prompt.strip()}"
    )


def review_diff(
    diff: str,
    model: str,
    api_key: str,
    *,
    custom_prompt: Optional[str] = None,
    chunk_index: Optional[int] = None,
    chunk_total: Optional[int] = None,
) -> str:
    client = OpenAI(api_key=api_key)
    chunk_note = ""
    if chunk_index is not None and chunk_total is not None and chunk_total > 1:
        chunk_note = (
            f"\n\nThis is chunk {chunk_index + 1} of {chunk_total}. "
            "Review only this portion; a later merge will combine findings.\n"
        )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": build_system_prompt(custom_prompt)},
            {
                "role": "user",
                "content": (
                    "Please review the following git diff for security "
                    "vulnerabilities and suggest refactoring steps:"
                    f"{chunk_note}\n\n"
                    f"```diff\n{diff}\n```"
                ),
            },
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content
    return content or "(No response from model.)"


def merge_chunk_reviews(reviews: list[str]) -> str:
    """Combine multi-chunk Markdown reviews into one report."""
    if len(reviews) == 1:
        return reviews[0]

    parts = ["# Combined review\n"]
    for i, review in enumerate(reviews, start=1):
        parts.append(f"## Chunk {i}\n\n{review.strip()}\n")
    return "\n".join(parts)
