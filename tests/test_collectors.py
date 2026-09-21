from src.collectors import collect_all, parse_rss


SOURCE = {"name": "OpenAI", "channel": "官方博客", "official": True}


def test_parse_rss_returns_normalized_candidate():
    xml = """<rss><channel><item><title>News</title><link>https://openai.com/news/x</link><pubDate>Sun, 20 Sep 2026 00:00:00 GMT</pubDate><description>Summary</description></item></channel></rss>"""
    items = parse_rss(xml, SOURCE)
    assert items[0].publisher == "OpenAI"
    assert items[0].official is True


def test_collect_all_isolates_source_failure():
    def loader(source):
        if source["name"] == "broken":
            raise ValueError("bad page")
        return []

    candidates, errors = collect_all([{"name": "good"}, {"name": "broken"}], loader=loader)
    assert candidates == []
    assert errors == [{"source": "broken", "error": "bad page"}]
