# AI-Powered CLI Code Reviewer

A terminal utility that reads your git diffs and uses the OpenAI API to suggest **security findings** and **refactoring steps**. Built for learning Cursor’s Terminal Agent while shipping a real CLI.

## Features

- Review unstaged, staged, commit, or branch diffs
- Path filters (ignore lockfiles / generated assets by default)
- Large-diff chunking so big PRs still fit in context
- Severity tags (`CRITICAL` → `INFO`) with CI-friendly `--fail-on`
- Output as Rich Markdown, plain Markdown, JSON, or raw text
- Optional `.reviewerrc` project config and custom prompt
- Installable package: `ai-reviewer`

## Requirements

- Python 3.10+
- Git
- An [OpenAI API key](https://platform.openai.com/api-keys)

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Copy the example env file and add your key:

```powershell
copy .env.example .env
```

```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

Optional project config:

```powershell
copy .reviewerrc.example .reviewerrc
```

## Usage

```powershell
ai-reviewer
# or
python reviewer.py
python -m ai_reviewer
```

By default the tool reviews unstaged changes, then falls back to staged changes if the working tree is clean.

### Options

| Flag | Description |
|------|-------------|
| `--staged` | Review only staged changes |
| `--commit REF` | Review a specific commit |
| `--base REF` | Diff against a base ref (e.g. `main`) |
| `--model TEXT` | Override the OpenAI model |
| `--config PATH` | Use a specific `.reviewerrc` |
| `--ignore GLOB` | Extra ignore pattern (repeatable) |
| `--include GLOB` | Only include matching paths |
| `--format rich\|markdown\|json\|raw` | Output format |
| `--output FILE` | Also write the review to a file |
| `--fail-on LEVEL` | Exit `2` if severity ≥ level (`none`/`critical`/`high`/…) |
| `--max-chunk-lines N` | Split large diffs into chunks |
| `--raw` | Alias for `--format raw` |
| `-h`, `--help` | Show help |

### Examples

```powershell
ai-reviewer --staged
ai-reviewer --base main --fail-on high
ai-reviewer --ignore "*.generated.py" --format json --output review.json
ai-reviewer --include "src/**/*.py" --output review.md --format markdown
```

### CI exit codes

| Code | Meaning |
|------|---------|
| `0` | OK / below threshold |
| `1` | Tool / API / config error |
| `2` | Findings met `--fail-on` threshold |

## Configuration (`.reviewerrc`)

JSON file discovered by walking up from the current directory:

```json
{
  "model": "gpt-4o-mini",
  "fail_on": "critical",
  "max_chunk_lines": 400,
  "output_format": "rich",
  "ignore": ["*.generated.py"],
  "include": [],
  "custom_prompt": "Prefer minimal refactors. Flag hardcoded secrets."
}
```

User `ignore` patterns are merged with sensible defaults (lockfiles, images, minified assets). Set `"replace_ignore": true` to replace defaults entirely.

## Project layout

```
ai_reviewer/
  cli.py          # Click entrypoint
  git_diff.py     # git integration
  filters.py      # path filters + chunking
  config.py       # .reviewerrc loading
  llm.py          # OpenAI client + prompts
  severity.py     # severity parsing / exit codes
  output.py       # Rich / JSON / file output
tests/            # unit tests (no API calls)
```

## Development

```powershell
pip install -e ".[dev]"
pytest -q
```

## Tech stack

- Python, Click, OpenAI SDK, python-dotenv, Rich
