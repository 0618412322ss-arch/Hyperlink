from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.collectors import collect_all
from src.pipeline import select_daily


def write_payload(articles: list[dict], output: Path, updated_at: str | None = None) -> bool:
    if not articles:
        return False
    output.mkdir(parents=True, exist_ok=True)
    stamp = updated_at or datetime.now(timezone.utc).isoformat()
    payload = {"updated_at": stamp, "articles": articles}
    fd, temp_name = tempfile.mkstemp(dir=output, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temp_name, output / "latest.json")
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("dist/data"))
    parser.add_argument("--sources", type=Path, default=Path("data/sources.json"))
    args = parser.parse_args()
    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    candidates, errors = collect_all(sources)
    articles = [a.to_public_dict() for a in select_daily(candidates)]
    if not write_payload(articles, args.output):
        print(json.dumps({"status": "preserved", "errors": errors}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "updated", "count": len(articles), "errors": errors}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
