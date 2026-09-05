"""테슬라 관련 뉴스/커뮤니티 RSS 수집."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import feedparser
import requests

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
TIMEOUT = 20


def _google_news(query: str, lang: str = "en") -> str:
    locales = {
        "en": "hl=en-US&gl=US&ceid=US:en",
        "ko": "hl=ko&gl=KR&ceid=KR:ko",
    }
    return (
        "https://news.google.com/rss/search?q="
        + requests.utils.quote(query)
        + "&"
        + locales[lang]
    )


# (표시용 출처 이름, 피드 URL)
SOURCES: list[tuple[str, str]] = [
    ("Google News", _google_news("Tesla TSLA stock when:1d")),
    ("Google News", _google_news("Tesla analyst price target rating when:1d")),
    ("Google News", _google_news("Tesla Elon Musk when:1d")),
    ("Google News", _google_news("TSLA earnings deliveries guidance when:1d")),
    ("구글뉴스", _google_news("테슬라 when:1d", "ko")),
    ("구글뉴스", _google_news("테슬라 주가 투자의견 when:1d", "ko")),
    (
        "Yahoo Finance",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=TSLA&region=US&lang=en-US",
    ),
    ("Seeking Alpha", "https://seekingalpha.com/api/sa/combined/TSLA.xml"),
    ("Electrek", "https://electrek.co/tag/tesla/feed/"),
    ("Teslarati", "https://www.teslarati.com/feed/"),
    ("InsideEVs", "https://insideevs.com/rss/articles/all/"),
    ("CleanTechnica", "https://cleantechnica.com/tag/tesla/feed/"),
    ("r/teslainvestorsclub", "https://www.reddit.com/r/teslainvestorsclub/hot/.rss"),
    ("r/TeslaMotors", "https://www.reddit.com/r/teslamotors/hot/.rss"),
    ("r/stocks", "https://www.reddit.com/r/stocks/search.rss?q=TSLA&restrict_sr=1&sort=new"),
]

RELEVANCE = re.compile(r"tesla|tsla|테슬라|elon musk|일론\s*머스크", re.I)

# 기관 지분공시(13F)를 템플릿으로 찍어내는 자동 생성 기사. 매일 수십 건씩 쏟아진다.
SPAM_TITLE = re.compile(
    r"makes (a )?new (investment|position|stake)"
    r"|takes (a )?(new )?(position|stake) in"
    r"|(buys|sells|acquires|purchases|holds) [\d,]+ shares"
    r"|(buys|sells|acquires) shares of"
    r"|shares (sold|bought|purchased|acquired) by"
    r"|(boosts|lowers|trims|grows|raises|reduces|lessens|cuts) (its |their )?(stock )?(position|holdings?|stake)"
    r"|(position|holdings?|stake) (boosted|lowered|lessened|raised|trimmed|increased|decreased|cut) by"
    r"|purchases new (shares|stake|position)"
    r"|has \$[\d.,]+ (million|billion)"
    r"|invests \$[\d.,]+ (million|billion) in",
    re.I,
)

# 콘텐츠팜·가십 매체. 새로 눈에 띄는 곳이 있으면 여기에 추가하면 된다.
SPAM_SOURCE = re.compile(
    r"marketbeat|defense world|etf daily news|american banking news|ticker report"
    r"|dispatch tribunal|modern readers|zolmax|macroaxis"
    r"|soap central|norada|basenor|blockonomi|blockchain\.news|ababnews|t2online|martin cid",
    re.I,
)


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: datetime | None
    summary: str = ""

    @property
    def text(self) -> str:
        return f"{self.title} {self.summary}"


def _clean(raw: str) -> str:
    """HTML 태그와 여분의 공백 제거."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw or "")).strip()


def _published(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def _source_name(default: str, entry) -> str:
    """구글뉴스는 원 매체명을 담고 있으므로 그쪽을 우선 사용."""
    origin = entry.get("source")
    if isinstance(origin, dict):
        title = origin.get("title")
        if title:
            return title
    return default


def _strip_source_suffix(title: str, source: str) -> str:
    """구글뉴스가 제목 끝에 붙이는 ' - 매체명'을 제거 (출처는 따로 표시하므로)."""
    suffix = f" - {source}"
    return title[: -len(suffix)] if title.endswith(suffix) else title


def parse_feed(name: str, body: str) -> list[Article]:
    parsed = feedparser.parse(body)
    articles = []
    for entry in parsed.entries:
        title = _clean(entry.get("title", ""))
        url = entry.get("link", "")
        if not title or not url:
            continue
        source = _source_name(name, entry)
        articles.append(
            Article(
                title=_strip_source_suffix(title, source),
                url=url,
                source=source,
                published=_published(entry),
                summary=_clean(entry.get("summary", ""))[:300],
            )
        )
    return articles


def _fetch_one(source: tuple[str, str]) -> list[Article]:
    name, url = source
    try:
        response = requests.get(
            url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[warn] {name} 수집 실패: {exc}")
        return []
    return parse_feed(name, response.text)


def is_spam(article: Article) -> bool:
    return bool(SPAM_TITLE.search(article.title) or SPAM_SOURCE.search(article.source))


def keep(article: Article, cutoff: datetime) -> bool:
    """최근 기사이면서, 테슬라 관련이고, 스팸이 아닌 것만 통과."""
    if article.published and article.published < cutoff:
        return False
    return bool(RELEVANCE.search(article.text)) and not is_spam(article)


def collect(hours: int = 24) -> list[Article]:
    """모든 소스에서 최근 `hours` 시간 내 테슬라 관련 기사를 모은다."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        batches = pool.map(_fetch_one, SOURCES)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    collected = [article for batch in batches for article in batch]
    fresh = [article for article in collected if keep(article, cutoff)]
    spam = sum(1 for article in collected if is_spam(article))
    print(f"[info] 수집 {len(collected)}건 → 통과 {len(fresh)}건 (스팸 {spam}건 제외)")
    return fresh
