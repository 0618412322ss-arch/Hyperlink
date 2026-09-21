from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from urllib.parse import urlparse


@dataclass(frozen=True)
class Candidate:
    title: str
    url: str
    published_at: datetime
    publisher: str
    channel: str
    excerpt: str = ""
    official: bool = False

    @classmethod
    def from_mapping(cls, raw: dict) -> "Candidate":
        for key in ("title", "url", "published_at", "publisher", "channel"):
            if not raw.get(key):
                raise ValueError(f"missing {key}")
        if urlparse(str(raw["url"])).scheme not in {"http", "https"}:
            raise ValueError("invalid url")
        stamp = raw["published_at"]
        if isinstance(stamp, str):
            stamp = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        return cls(
            title=str(raw["title"]).strip(), url=str(raw["url"]),
            published_at=stamp, publisher=str(raw["publisher"]).strip(),
            channel=str(raw["channel"]).strip(),
            excerpt=str(raw.get("excerpt", "")).strip(),
            official=bool(raw.get("official", False)),
        )


@dataclass(frozen=True)
class SourceLink:
    name: str
    url: str
    primary: bool = False


@dataclass(frozen=True)
class Verification:
    status: str
    note: str
    checked_at: datetime


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    published_at: datetime
    background: str
    summary: str
    impact: str
    category: str
    publisher: str
    channel: str
    verification: Verification
    sources: tuple[SourceLink, ...]
    tags: tuple[str, ...]

    def to_public_dict(self) -> dict:
        payload = asdict(self)
        payload["published_at"] = self.published_at.isoformat()
        payload["verification"]["checked_at"] = self.verification.checked_at.isoformat()
        payload["tags"] = list(self.tags)
        payload["sources"] = [asdict(item) for item in self.sources]
        return payload
