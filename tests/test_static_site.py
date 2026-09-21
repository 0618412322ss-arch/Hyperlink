import json
from pathlib import Path


def test_site_has_accessible_editorial_landmarks():
    html = Path("dist/index.html").read_text(encoding="utf-8")
    for marker in ("<header", "<main", "<footer", 'id="news-grid"', 'id="source-filters"'):
        assert marker in html
    assert "跳到主要内容" in html


def test_latest_contains_six_verified_source_backed_articles():
    payload = json.loads(Path("dist/data/latest.json").read_text(encoding="utf-8"))
    assert len(payload["articles"]) == 6
    assert all(a["verification"]["status"] == "verified" for a in payload["articles"])
    assert all(a["sources"] and a["sources"][0]["url"].startswith("https://") for a in payload["articles"])
