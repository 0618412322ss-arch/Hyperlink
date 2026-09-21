import json
from pathlib import Path

from scripts.update_news import write_payload


def test_zero_articles_preserves_existing_file(tmp_path):
    target = tmp_path / "latest.json"
    target.write_text('{"keep": true}', encoding="utf-8")
    assert write_payload([], tmp_path) is False
    assert json.loads(target.read_text(encoding="utf-8")) == {"keep": True}


def test_valid_articles_are_written_atomically(tmp_path):
    assert write_payload([{"id": "one"}], tmp_path, updated_at="2026-09-20T00:00:00Z") is True
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["articles"] == [{"id": "one"}]
