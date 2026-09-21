from datetime import datetime, timezone

from src.models import Candidate
from src.pipeline import deduplicate, select_daily, verify_cluster


def item(title, url, publisher="OpenAI", official=True):
    return Candidate(title, url, datetime(2026, 9, 20, tzinfo=timezone.utc), publisher, "官方博客", "一项重要更新。", official)


def test_duplicate_event_uses_one_slot():
    groups = deduplicate([
        item("OpenAI 发布模型安全报告", "https://openai.com/a"),
        item("OpenAI：模型安全报告正式发布", "https://example.com/b", "媒体", False),
    ])
    assert len(groups) == 1


def test_unofficial_single_source_is_pending():
    assert verify_cluster([item("传闻", "https://example.com/a", "媒体", False)]).status == "pending"


def test_two_independent_sources_verify_nonofficial_story():
    cluster = [
        item("同一消息", "https://one.example/a", "媒体甲", False),
        item("同一消息", "https://two.example/b", "媒体乙", False),
    ]
    assert verify_cluster(cluster).status == "verified"


def test_select_daily_does_not_pad_unverified_items():
    picked = select_daily([
        item("可靠消息", "https://openai.com/a"),
        item("传闻", "https://rumor.example/a", "匿名", False),
    ])
    assert len(picked) == 1
    assert picked[0].title == "可靠消息"
