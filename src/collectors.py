from __future__ import annotations

import feedparser
import requests
from bs4 import BeautifulSoup

from .models import Candidate


def parse_rss(text: str, source: dict) -> list[Candidate]:
    feed = feedparser.parse(text)
    results = []
    for entry in feed.entries:
        raw = {
            "title": entry.get("title"), "url": entry.get("link"),
            "published_at": entry.get("published") or entry.get("updated"),
            "publisher": source["name"], "channel": source.get("channel", "公开渠道"),
            "excerpt": BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True),
            "official": source.get("official", False),
        }
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed:
            from datetime import datetime, timezone
            raw["published_at"] = datetime(*parsed[:6], tzinfo=timezone.utc)
        try:
            results.append(Candidate.from_mapping(raw))
        except (ValueError, TypeError):
            continue
    return results


def collect_source(source: dict) -> list[Candidate]:
    response = requests.get(source["url"], timeout=15, headers={"User-Agent": "AI-News-Daily/1.0"})
    response.raise_for_status()
    return parse_rss(response.text, source)


def collect_all(sources: list[dict], loader=collect_source):
    candidates, errors = [], []
    for source in sources:
        try:
            candidates.extend(loader(source))
        except (requests.RequestException, ValueError) as exc:
            errors.append({"source": source["name"], "error": str(exc)})
    return candidates, errors
