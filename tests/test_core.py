from pathlib import Path

from ai_reviewer.config import ReviewerConfig, load_config
from ai_reviewer.filters import chunk_diff, filter_diff, parse_diff_files
from ai_reviewer.severity import (
    exit_code_for,
    extract_highest_severity,
    should_fail,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample.diff"


def test_parse_diff_files():
    diff = FIXTURE.read_text(encoding="utf-8")
    files = parse_diff_files(diff)
    paths = [f.path for f in files]
    assert paths == ["app/auth.py", "package-lock.json", "app/utils.py"]


def test_filter_ignores_lockfile():
    diff = FIXTURE.read_text(encoding="utf-8")
    filtered, kept, skipped = filter_diff(diff, ignore=["package-lock.json"])
    assert "package-lock.json" in skipped
    assert "app/auth.py" in kept
    assert "package-lock.json" not in filtered
    assert "app/auth.py" in filtered


def test_filter_include_only_python():
    diff = FIXTURE.read_text(encoding="utf-8")
    filtered, kept, skipped = filter_diff(diff, include=["*.py"])
    assert set(kept) == {"app/auth.py", "app/utils.py"}
    assert "package-lock.json" in skipped
    assert "lockfileVersion" not in filtered


def test_chunk_diff_respects_file_boundaries():
    diff = FIXTURE.read_text(encoding="utf-8")
    chunks = chunk_diff(diff, max_lines=12)
    assert len(chunks) >= 2
    assert all(chunk.strip() for chunk in chunks)


def test_extract_highest_severity():
    review = """
## Security findings
- **[HIGH]** `app/auth.py`: SQL injection
- **[CRITICAL]** `app/auth.py`: hardcoded secret

## Summary
Bad stuff.
Highest severity: CRITICAL
"""
    assert extract_highest_severity(review) == "CRITICAL"


def test_fail_on_threshold():
    assert should_fail("CRITICAL", "critical")
    assert should_fail("HIGH", "high")
    assert not should_fail("MEDIUM", "high")
    assert not should_fail("CRITICAL", "none")
    assert exit_code_for("HIGH", "high") == 2
    assert exit_code_for("LOW", "high") == 0


def test_load_config_merges_ignore(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / ".reviewerrc"
    config_file.write_text(
        '{"ignore": ["*.generated.py"], "fail_on": "high", "model": "gpt-4o"}',
        encoding="utf-8",
    )
    cfg = load_config()
    assert cfg.model == "gpt-4o"
    assert cfg.fail_on == "high"
    assert "package-lock.json" in cfg.ignore
    assert "*.generated.py" in cfg.ignore


def test_config_from_dict_replace_ignore():
    cfg = ReviewerConfig.from_dict(
        {"ignore": ["only-this"], "replace_ignore": True}
    )
    assert cfg.ignore == ["only-this"]
