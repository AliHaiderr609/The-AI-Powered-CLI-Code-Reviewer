# AI-Powered CLI Code Reviewer

A small terminal utility that reads your git diffs and uses the OpenAI API to suggest security findings and refactoring steps.

## Requirements

- Python 3.10+
- Git
- An [OpenAI API key](https://platform.openai.com/api-keys)

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy the example env file and add your key:

```powershell
copy .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

## Usage

From a git repository with local changes:

```powershell
python reviewer.py
```

By default the tool reviews unstaged changes, then falls back to staged changes if the working tree is clean.

### Options

| Flag | Description |
|------|-------------|
| `--staged` | Review only staged changes (`git diff --cached`) |
| `--commit REF` | Review a specific commit (e.g. `HEAD` or `abc1234`) |
| `--base REF` | Diff against a base ref (e.g. `main`) |
| `--model TEXT` | Override the OpenAI model |
| `--raw` | Print plain text instead of Rich Markdown |
| `-h`, `--help` | Show help |

### Examples

```powershell
python reviewer.py --staged
python reviewer.py --commit HEAD
python reviewer.py --base main
python reviewer.py --model gpt-4o
```

## How it works

1. Collects a git diff from the current repo
2. Sends the diff to OpenAI with a security/refactoring-focused prompt
3. Prints a Markdown report with **Security findings**, **Refactoring steps**, and a **Summary**

## Tech stack

- Python
- [Click](https://click.palletsprojects.com/) — CLI
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [python-dotenv](https://github.com/theskumar/python-dotenv) — env loading
- [Rich](https://rich.readthedocs.io/) — terminal output
