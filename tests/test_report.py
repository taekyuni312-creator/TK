from datetime import datetime, timedelta, timezone
from pathlib import Path

from tesla_news import feeds, report
from tesla_news.quote import Quote

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 5, 6, 0, tzinfo=timezone.utc)


def load(name, source):
    return feeds.parse_feed(source, (FIXTURES / name).read_text())


def fresh(articles, hours=24):
    cutoff = NOW - timedelta(hours=hours)
    return [a for a in articles if feeds.keep(a, cutoff)]


def test_parse_extracts_fields_and_origin_source():
    articles = load("google_news.xml", "Google News")
    assert len(articles) == 5
    first = articles[0]
    assert first.source == "Reuters"  # 구글뉴스 대신 원 매체명
    assert first.published == datetime(2026, 9, 5, 4, 0, tzinfo=timezone.utc)
    assert "<p>" not in first.summary  # HTML 태그 제거


def test_filters_irrelevant_and_stale():
    titles = [a.title for a in fresh(load("google_news.xml", "Google News"))]
    assert not any("MacBook" in t for t in titles)  # 테슬라 무관
    assert not any("Q3 deliveries" in t for t in titles)  # 24시간 초과


def test_dedupe_matches_same_headline_from_different_outlets():
    kept = report.dedupe(fresh(load("google_news.xml", "Google News")))
    assert len(kept) == 2
    assert kept[0].source == "Reuters"


def test_categorize_by_keyword_and_by_community_source():
    articles = fresh(load("google_news.xml", "Google News")) + load("reddit.xml", "r/teslainvestorsclub")
    buckets = report.categorize(report.dedupe(articles))
    assert [a.title for a in buckets["🎯 애널리스트·투자의견"]][0].startswith("Tesla stock surges")
    assert "Cybertrucks" in buckets["⚖️ 규제·리스크"][0].title
    assert buckets[report.COMMUNITY][0].source == "r/teslainvestorsclub"


def test_build_renders_quote_relative_time_and_escapes_html():
    articles = fresh(load("google_news.xml", "Google News")) + load("reddit.xml", "r/teslainvestorsclub")
    message = report.build(articles, Quote(430.0, 400.0, "Yahoo Finance"), now=NOW)
    assert "TSLA $430.00" in message and "(+7.50%)" in message
    assert "2시간 전" in message  # 04:00 UTC 기사, 기준 06:00 UTC
    assert "drawdown &amp; adding" in message  # & 이스케이프
    assert "holding TSLA through" in message
    assert "총 3건 수집" in message


def test_build_without_quote_and_without_articles():
    message = report.build([], None, now=NOW)
    assert "조회 실패" in message
    assert "수집된 기사가 없습니다" in message


def test_split_respects_limit_and_keeps_every_line():
    message = report.build(
        [
            feeds.Article(f"Tesla headline number {i}", f"https://e.com/{i}", "Src", NOW)
            for i in range(60)
        ],
        None,
        now=NOW,
    )
    chunks = report.split(message, limit=500)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)
    assert "\n".join(chunks) == message


def test_google_news_source_suffix_stripped_from_title():
    articles = load("google_news.xml", "Google News")
    assert articles[0].title == "Tesla stock surges as analyst raises price target to $500"
    assert articles[0].source == "Reuters"


def korean(title, hours_ago=1, source="뉴시스"):
    return feeds.Article(title, f"https://kr.example/{abs(hash(title))}", source, NOW - timedelta(hours=hours_ago))


def english(title, hours_ago=1, source="Reuters"):
    return feeds.Article(title, f"https://en.example/{abs(hash(title))}", source, NOW - timedelta(hours=hours_ago))


def test_korean_articles_are_listed_before_foreign_ones():
    articles = [english("Tesla stock jumps on Cybercab", 1), korean("테슬라 주가 사이버캡에 급등", 9)]
    message = report.build(articles, None, now=NOW)
    assert message.index("테슬라 주가 사이버캡에") < message.index("Tesla stock jumps")


def test_highlights_rank_topics_by_coverage_with_outlet_count():
    articles = (
        [english(f"Tesla Cybercab robotaxi report {i}", 1, f"Outlet{i}") for i in range(6)]
        + [english(f"Tesla analyst raises price target {i}", 2, "stocktwits") for i in range(3)]
        + [english("Tesla opens a new store", 3)]
    )
    message = report.build(articles, None, now=NOW)
    assert "📌 <b>오늘의 핵심</b>" in message
    assert "① <b>사이버캡·로보택시</b> — 6건 / 6개 매체" in message
    assert "② <b>목표주가·투자의견</b> — 3건 / 1개 매체" in message


def test_highlights_omitted_when_no_topic_reaches_the_threshold():
    message = report.build([english("Tesla opens a new store in Busan")], None, now=NOW)
    assert "오늘의 핵심" not in message


def test_highlight_lead_prefers_a_korean_headline():
    articles = [english(f"Tesla Cybercab news {i}", 1) for i in range(4)] + [
        korean("테슬라 사이버캡 오스틴 투입", 20)
    ]
    message = report.build(articles, None, now=NOW)
    highlight = message.split("① ")[1]
    assert "테슬라 사이버캡 오스틴 투입" in highlight.split("\n")[1]


def test_split_keeps_blank_lines_at_chunk_boundaries():
    message = "\n".join(f"line {i}" if i % 3 else "" for i in range(200))
    chunks = report.split(message, limit=60)
    assert "\n".join(chunks) == message


def test_overlapping_topics_do_not_repeat_the_same_lead_article():
    """한 기사가 여러 주제에 걸려도 대표 기사는 중복 노출되지 않는다."""
    articles = [korean(f"테슬라 사이버캡 로보택시 FSD 자율주행 소식 {i}", i + 1) for i in range(6)]
    message = report.build(articles, None, now=NOW)
    leads = [line.strip() for line in message.split("\n") if line.startswith("   <a")]
    assert len(leads) >= 2
    assert len(set(leads)) == len(leads)
