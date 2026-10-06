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
    assert buckets["🎯 애널리스트·투자의견"][0].lead.title.startswith("Tesla stock surges")
    assert "Cybertrucks" in buckets["⚖️ 규제·리스크"][0].lead.title
    assert buckets[report.COMMUNITY][0].lead.source == "r/teslainvestorsclub"


def test_build_renders_quote_relative_time_and_escapes_html():
    articles = fresh(load("google_news.xml", "Google News")) + load("reddit.xml", "r/teslainvestorsclub")
    message = report.build(articles, Quote(430.0, 400.0, "Yahoo Finance"), now=NOW)
    assert "TSLA $430.00" in message and "(+7.50%)" in message
    assert "2시간 전" in message  # 04:00 UTC 기사, 기준 06:00 UTC
    assert "drawdown &amp; adding" in message  # & 이스케이프
    assert "holding TSLA through" in message
    assert "기사 3건" in message


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
    chunks = report.split(message, limit=200)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
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
    """묶음 수가 같으면 한국어 기사를 먼저 보여준다."""
    articles = [english("Tesla Cybertruck output climbs", 1), korean("테슬라 FSD 자율주행 업데이트 배포", 1)]
    message = report.build(articles, None, now=NOW)
    assert message.index("테슬라 FSD 자율주행") < message.index("Tesla Cybertruck output")


def test_merging_keeps_the_korean_headline_as_the_representative():
    articles = [english("Tesla stock jumps on Cybercab robotaxi", 1), korean("테슬라 주가 사이버캡에 급등", 9)]
    message = report.build(articles, None, now=NOW)
    assert "테슬라 주가 사이버캡에 급등" in message
    assert "Tesla stock jumps" not in message


def test_same_topic_in_one_sector_collapses_to_a_single_line():
    """같은 섹터에서 같은 사건을 다룬 여러 매체 기사는 한 줄로 합쳐진다."""
    articles = [
        korean("운전대 없는 테슬라 '사이버캡' 유료 운행…美 당국 조사 착수", 12, "재경일보"),
        korean("美 정부, '핸들·페달 없는' 테슬라 사이버캡 조사 착수", 15, "엠투데이"),
        korean("테슬라 사이버캡 1000대, 미 당국 인증 조사", 10, "tokenpost"),
    ]
    buckets = report.categorize(report.dedupe(articles))
    stories = buckets["⚖️ 규제·리스크"]
    assert len(stories) == 1
    assert stories[0].outlets == 3


def test_same_topic_in_different_sectors_stays_separate():
    """주제가 같아도 섹터가 다르면 합치지 않는다 — 실적과 규제는 다른 소식이다."""
    articles = [
        english("Tesla Cybercab draws an NHTSA probe hours after launch", 3, "AP"),
        english("Tesla Q3 revenue jumps 26% even as Cybercab stumbles", 4, "Bloomberg"),
    ]
    buckets = report.categorize(report.dedupe(articles))
    assert len(buckets["⚖️ 규제·리스크"]) == 1
    assert len(buckets["💰 실적·재무"]) == 1


def test_widely_covered_stories_come_first():
    articles = [english("Tesla opens a new Gigafactory line", 1, "Solo")] + [
        english(f"Tesla Cybercab robotaxi fleet expands {i}", 2, f"Outlet{i}") for i in range(4)
    ]
    buckets = report.categorize(report.dedupe(articles))
    product = buckets["🔧 제품·기술"]
    assert product[0].outlets == 4
    assert product[0].outlets > product[1].outlets


def test_highlight_story_is_not_repeated_in_its_sector():
    """핵심에 올라간 묶음은 아래 섹터 목록에서 빠진다."""
    articles = [
        english(f"Tesla Cybercab robotaxi probe opens {i}", 2, f"Outlet{i}") for i in range(5)
    ] + [english("Tesla battery supplier signs a 4680 deal", 1, "Reuters")]
    message = report.build(articles, None, now=NOW)
    assert message.count("Cybercab robotaxi probe opens") == 1


def test_highlights_label_the_sector_and_the_outlet_count():
    articles = [english(f"Tesla Cybercab robotaxi probe opens {i}", 2, f"Outlet{i}") for i in range(5)]
    message = report.build(articles, None, now=NOW)
    assert "📌 <b>오늘의 핵심</b>" in message
    assert "① <b>⚖️ 규제·리스크</b> · 5개 매체가 보도" in message


def test_a_thinly_covered_story_stays_out_of_the_highlights():
    articles = [english(f"Tesla Cybercab robotaxi probe opens {i}", 2, f"Outlet{i}") for i in range(2)]
    message = report.build(articles, None, now=NOW)
    assert "오늘의 핵심" not in message


def test_merged_story_shows_how_many_outlets_backed_it():
    articles = [english(f"Tesla Cybercab robotaxi probe opens {i}", 2, f"Outlet{i}") for i in range(3)]
    message = report.build([*articles, english("Tesla picks a new CFO", 1, "WSJ")], None, now=NOW)
    assert "+2개 매체" in message or "3개 매체가 보도" in message


def test_split_keeps_blank_lines_at_chunk_boundaries():
    message = "\n".join(f"line {i}" if i % 3 else "" for i in range(200))
    chunks = report.split(message, limit=60)
    assert "\n".join(chunks) == message
