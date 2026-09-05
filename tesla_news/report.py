"""수집한 기사를 카테고리별 텔레그램 메시지로 정리."""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone

from .feeds import Article
from .quote import Quote

KST = timezone(timedelta(hours=9))
WEEKDAYS = "월화수목금토일"
MAX_MESSAGE = 3800  # 텔레그램 4096자 제한 대비 여유
MAX_PER_CATEGORY = 5

KOREAN = re.compile(r"[가-힣]")

# (카테고리 이름, 매칭 정규식). 위에서부터 먼저 걸리는 카테고리로 분류된다.
CATEGORIES: list[tuple[str, re.Pattern]] = [
    (
        "🎯 애널리스트·투자의견",
        re.compile(
            r"analyst|price target|upgrade|downgrade|\brating\b|outperform|underperform"
            r"|overweight|underweight|initiated coverage|buy rating|sell rating"
            r"|애널리스트|목표주가|투자의견|매수의견",
            re.I,
        ),
    ),
    (
        "💰 실적·재무",
        re.compile(
            r"earnings|revenue|deliveries|delivery numbers|guidance|margin|quarterly"
            r"|free cash flow|실적|인도량|매출|영업이익|가이던스",
            re.I,
        ),
    ),
    (
        "📈 주가·시장",
        re.compile(
            r"\bstock\b|shares|\btsla\b|rally|plunge|surge|slump|market cap|short seller"
            r"|options|투자자|주가|급등|급락|시가총액|공매도|증시",
            re.I,
        ),
    ),
    (
        "⚖️ 규제·리스크",
        re.compile(
            r"lawsuit|recall|nhtsa|\bsec\b|probe|investigation|fine|subpoena|tariff"
            r"|리콜|소송|조사|규제|과징금|관세",
            re.I,
        ),
    ),
    (
        "🔧 제품·기술",
        re.compile(
            r"model [3sxy]|cybertruck|\bfsd\b|full self.driving|autopilot|robotaxi|optimus"
            r"|semi\b|4680|battery|gigafactory|megapack|사이버트럭|로보택시|자율주행|배터리",
            re.I,
        ),
    ),
    ("📰 기타 소식", re.compile(r".")),
]

COMMUNITY = "🗣 투자자 커뮤니티 여론"
COMMUNITY_SOURCES = re.compile(r"^r/|reddit", re.I)

# "오늘의 핵심"을 뽑을 관심 주제. 한 기사가 여러 주제에 걸쳐도 된다.
TOPICS: list[tuple[str, re.Pattern]] = [
    ("사이버캡·로보택시", re.compile(r"cybercab|robotaxi|사이버캡|로보택시", re.I)),
    ("FSD·자율주행", re.compile(r"\bfsd\b|full self.driving|autopilot|자율주행|오토파일럿", re.I)),
    ("규제·당국 조사", re.compile(r"nhtsa|probe|investigation|recall|\bsec\b|규제|조사|리콜", re.I)),
    ("목표주가·투자의견", re.compile(r"price target|analyst|upgrade|downgrade|목표주가|애널리스트|투자의견", re.I)),
    ("실적·인도량", re.compile(r"earnings|deliveries|revenue|guidance|실적|인도량|매출", re.I)),
    ("사이버트럭", re.compile(r"cybertruck|사이버트럭", re.I)),
    ("옵티머스·AI", re.compile(r"optimus|\bai\b|dojo|옵티머스|인공지능", re.I)),
    ("SpaceX·머스크", re.compile(r"spacex|starlink|스페이스x|스타링크", re.I)),
    ("배터리·에너지", re.compile(r"4680|battery|megapack|energy storage|배터리|메가팩|에너지", re.I)),
    ("중국·관세", re.compile(r"china|tariff|중국|관세", re.I)),
    ("모델Y·모델3", re.compile(r"model [3y]|모델\s*[3y]|모델와이", re.I)),
]
MIN_TOPIC_HITS = 3
MAX_TOPICS = 3


def _is_korean(article: Article) -> bool:
    return bool(KOREAN.search(article.title))


def _when(article: Article) -> float:
    return article.published.timestamp() if article.published else 0.0


def _reading_order(article: Article) -> tuple:
    """한국어 기사를 먼저, 그다음 최신순."""
    return (not _is_korean(article), -_when(article))


def _normalize(title: str) -> str:
    """중복 판정용 키. 구글뉴스가 붙이는 ' - 매체명' 꼬리표를 떼어낸다."""
    stripped = re.sub(r"\s+-\s+[^-]{2,40}$", "", title)
    return re.sub(r"[^a-z0-9가-힣]", "", stripped.lower())[:60]


def dedupe(articles: list[Article]) -> list[Article]:
    seen_url: set[str] = set()
    seen_title: set[str] = set()
    unique = []
    for article in articles:
        key = _normalize(article.title)
        if article.url in seen_url or (key and key in seen_title):
            continue
        seen_url.add(article.url)
        seen_title.add(key)
        unique.append(article)
    return unique


def categorize(articles: list[Article]) -> dict[str, list[Article]]:
    buckets: dict[str, list[Article]] = {}
    for article in articles:
        if COMMUNITY_SOURCES.search(article.source):
            name = COMMUNITY
        else:
            name = next(n for n, pattern in CATEGORIES if pattern.search(article.text))
        buckets.setdefault(name, []).append(article)

    for bucket in buckets.values():
        bucket.sort(key=_reading_order)
    return buckets


def top_topics(articles: list[Article]) -> list[tuple[str, list[Article]]]:
    """오늘 가장 많이 보도된 주제 순으로. 최소 건수를 못 넘기면 뺀다."""
    hits = [(name, [a for a in articles if pattern.search(a.text)]) for name, pattern in TOPICS]
    ranked = sorted(
        (hit for hit in hits if len(hit[1]) >= MIN_TOPIC_HITS),
        key=lambda hit: len(hit[1]),
        reverse=True,
    )
    return ranked[:MAX_TOPICS]


def _ago(published: datetime | None, now: datetime) -> str:
    if not published:
        return "시각 미상"
    minutes = int((now - published).total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 0)}분 전"
    if minutes < 60 * 24:
        return f"{minutes // 60}시간 전"
    return f"{minutes // (60 * 24)}일 전"


def _quote_line(quote: Quote | None) -> str:
    if not quote:
        return "📊 TSLA 시세: 조회 실패"
    arrow = "🔺" if quote.change >= 0 else "🔻"
    return (
        f"📊 <b>TSLA ${quote.price:,.2f}</b> {arrow} "
        f"{quote.change:+,.2f} ({quote.change_pct:+.2f}%)"
    )


def _link(article: Article) -> str:
    title = html.escape(article.title, quote=False)
    url = html.escape(article.url, quote=True)
    return f'<a href="{url}">{title}</a>'


def _highlights(articles: list[Article]) -> list[str]:
    ranked = top_topics(articles)
    if not ranked:
        return []

    lines = ["📌 <b>오늘의 핵심</b>"]
    used: set[str] = set()
    for number, (name, bucket) in zip("①②③", ranked):
        outlets = len({article.source for article in bucket})
        # 주제가 겹치면 대표 기사도 겹치므로, 아직 안 쓴 기사를 우선 고른다.
        ordered = sorted(bucket, key=_reading_order)
        lead = next((a for a in ordered if a.url not in used), ordered[0])
        used.add(lead.url)
        lines.append(f"{number} <b>{name}</b> — {len(bucket)}건 / {outlets}개 매체")
        lines.append(f"   {_link(lead)}")
    lines.append("")
    return lines


def build(articles: list[Article], quote: Quote | None, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    kst = now.astimezone(KST)
    stamp = f"{kst:%Y-%m-%d} ({WEEKDAYS[kst.weekday()]}) {kst:%H:%M} KST"

    lines = ["🚗 <b>테슬라 데일리 브리핑</b>", stamp, "", _quote_line(quote), ""]

    unique = dedupe(articles)
    if not unique:
        lines.append("최근 24시간 내 수집된 기사가 없습니다.")
        return "\n".join(lines)

    lines += _highlights(unique)

    buckets = categorize(unique)
    for name in [n for n, _ in CATEGORIES] + [COMMUNITY]:
        bucket = buckets.get(name)
        if not bucket:
            continue
        lines.append(f"<b>{name}</b> ({len(bucket)}건)")
        for article in bucket[:MAX_PER_CATEGORY]:
            flag = "🇰🇷" if _is_korean(article) else "🌐"
            meta = f"{html.escape(article.source, quote=False)} · {_ago(article.published, now)}"
            lines.append(f"{flag} {_link(article)}\n     <i>{meta}</i>")
        if len(bucket) > MAX_PER_CATEGORY:
            lines.append(f"     <i>… 외 {len(bucket) - MAX_PER_CATEGORY}건</i>")
        lines.append("")

    lines.append(f"총 {len(unique)}건 수집")
    return "\n".join(lines)


def split(message: str, limit: int = MAX_MESSAGE) -> list[str]:
    """줄 단위로 텔레그램 길이 제한에 맞춰 나눈다."""
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for line in message.split("\n"):
        extra = len(line) + (1 if current else 0)
        if current and length + extra > limit:
            chunks.append("\n".join(current))
            current, length, extra = [], 0, len(line)
        current.append(line)
        length += extra
    if current:
        chunks.append("\n".join(current))
    return chunks
