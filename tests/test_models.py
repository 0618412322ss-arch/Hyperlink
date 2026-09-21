from datetime import datetime, timezone

import pytest

from src.models import Article, Candidate, SourceLink, Verification


def test_candidate_rejects_missing_title():
    with pytest.raises(ValueError, match="title"):
        Candidate.from_mapping({"url": "https://openai.com/news/"})


def test_candidate_rejects_non_http_url():
    raw = {
        "title": "Example",
        "url": "javascript:alert(1)",
        "published_at": "2026-09-20T00:00:00+00:00",
        "publisher": "OpenAI",
        "channel": "官方博客",
    }
    with pytest.raises(ValueError, match="url"):
        Candidate.from_mapping(raw)


def test_public_article_contains_required_sections():
    stamp = datetime(2026, 9, 20, tzinfo=timezone.utc)
    article = Article(
        id="example",
        title="Example",
        published_at=stamp,
        background="背景",
        summary="内容",
        impact="影响",
        category="国际",
        publisher="OpenAI",
        channel="官方博客",
        verification=Verification("verified", "官方原始来源", stamp),
        sources=(SourceLink("OpenAI", "https://openai.com/news/", True),),
        tags=("OpenAI",),
    )
    payload = article.to_public_dict()
    assert set(payload) >= {
        "id", "title", "published_at", "background", "summary", "impact",
        "category", "publisher", "channel", "verification", "sources", "tags",
    }
    assert payload["published_at"] == "2026-09-20T00:00:00+00:00"
