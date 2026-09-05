from datetime import datetime, timezone
from pathlib import Path

from tesla_news import feeds

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 9, 5, 6, 0, tzinfo=timezone.utc)
CUTOFF = datetime(2026, 9, 4, 6, 0, tzinfo=timezone.utc)


def kept_titles():
    articles = feeds.parse_feed("Google News", (FIXTURES / "spam.xml").read_text())
    return [a.title for a in articles if feeds.keep(a, CUTOFF)]


def test_13f_filing_churn_is_dropped():
    titles = kept_titles()
    for dropped in ("Makes New Investment", "Boosts Stock Holdings", "Shares Sold by", "Acquires 12,500 Shares"):
        assert not any(dropped in t for t in titles), dropped


def test_gossip_content_farm_is_dropped():
    assert not any("Influencer" in t for t in kept_titles())


def test_real_news_survives_the_filter():
    """실적·인수·기관 매매 '뉴스'까지 걸러버리면 안 된다."""
    titles = kept_titles()
    assert any("497,000 vehicles" in t for t in titles)
    assert any("acquires battery startup" in t for t in titles)
    assert any("Ark Invest sells $110 million" in t for t in titles)
