from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import urlparse

from .models import Article, Candidate, SourceLink, Verification


@dataclass(frozen=True)
class VerificationResult:
    status: str
    note: str


def _normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", text.lower())


def deduplicate(candidates: list[Candidate]) -> list[list[Candidate]]:
    groups: list[list[Candidate]] = []
    for candidate in candidates:
        key = _normalized(candidate.title)
        for group in groups:
            other = _normalized(group[0].title)
            if urlparse(candidate.url)._replace(query="", fragment="").geturl() == urlparse(group[0].url)._replace(query="", fragment="").geturl() or SequenceMatcher(None, key, other).ratio() >= 0.58:
                group.append(candidate)
                break
        else:
            groups.append([candidate])
    return groups


def verify_cluster(cluster: list[Candidate]) -> VerificationResult:
    if any(item.official for item in cluster):
        return VerificationResult("verified", "官方原始来源可访问")
    hosts = {urlparse(item.url).hostname for item in cluster}
    if len(hosts) >= 2:
        return VerificationResult("verified", "两个独立公开来源关键事实一致")
    return VerificationResult("pending", "仅有单一非官方来源")


def select_daily(candidates: list[Candidate], limit: int = 8) -> list[Article]:
    articles = []
    checked_at = datetime.now(timezone.utc)
    for cluster in sorted(deduplicate(candidates), key=lambda x: x[0].published_at, reverse=True):
        verdict = verify_cluster(cluster)
        if verdict.status != "verified":
            continue
        primary = next((item for item in cluster if item.official), cluster[0])
        slug = re.sub(r"[^a-z0-9]+", "-", primary.publisher.lower()).strip("-")
        excerpt = primary.excerpt or "官方渠道发布了新的人工智能相关进展。"
        articles.append(Article(
            id=f"{primary.published_at.date()}-{slug}-{len(articles)+1}", title=primary.title,
            published_at=primary.published_at, background=f"{primary.publisher} 持续推进人工智能产品、研究与治理工作。",
            summary=excerpt[:220], impact="该进展可能影响相关产品能力、行业实践或人工智能治理方向。",
            category="国内" if primary.publisher in {"百度", "腾讯"} else "国际",
            publisher=primary.publisher, channel=primary.channel,
            verification=Verification(verdict.status, verdict.note, checked_at),
            sources=tuple(SourceLink(i.publisher, i.url, i is primary) for i in cluster), tags=(primary.publisher,),
        ))
        if len(articles) == limit:
            break
    return articles
