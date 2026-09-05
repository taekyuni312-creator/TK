"""수집한 기사를 카테고리별 텔레그램 메시지로 정리."""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone

from .feeds import Article
from .quote import Quote

KST = timezone(timedelta(hours=9))
MAX_MESSAGE = 3800  # 텔레그램 4096자 제한 대비 여유
MAX_PER_CATEGORY = 8

# (카테고리 이름, 매칭 정규식). 위에서부터 먼저 걸리는 카테고리로 분류된다.
CATEGORIES: list[tuple[str, re.Pattern]] = [
    (
        "🎯 애널리스트·투자의견",
        re.compile(
            r"analyst|price target|upgrade|downgrade|\brating\b|outperform|underperform"
            r"|overweight|underweight|initiated coverage|buy rating|sell rating"
            r"|애널리스트|목표주가|투자의견|매수의견|투자의견",
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
        bucket.sort(key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return buckets


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
        f"{quote.change:+,.2f} ({quote.change_pct:+.2f}%) · {quote.source}"
    )


def build(articles: list[Article], quote: Quote | None, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    stamp = now.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")

    lines = [f"🚗 <b>테슬라 데일리 브리핑</b>", stamp, "", _quote_line(quote), ""]

    buckets = categorize(dedupe(articles))
    if not buckets:
        lines.append("최근 24시간 내 수집된 기사가 없습니다.")
        return "\n".join(lines)

    order = [name for name, _ in CATEGORIES] + [COMMUNITY]
    total = 0
    for name in order:
        bucket = buckets.get(name)
        if not bucket:
            continue
        lines.append(f"<b>{name}</b> ({len(bucket)}건)")
        for article in bucket[:MAX_PER_CATEGORY]:
            title = html.escape(article.title, quote=False)
            url = html.escape(article.url, quote=True)
            meta = f"{html.escape(article.source, quote=False)} · {_ago(article.published, now)}"
            lines.append(f'• <a href="{url}">{title}</a>\n  <i>{meta}</i>')
        if len(bucket) > MAX_PER_CATEGORY:
            lines.append(f"  <i>… 외 {len(bucket) - MAX_PER_CATEGORY}건</i>")
        lines.append("")
        total += len(bucket)

    lines.append(f"총 {total}건 수집")
    return "\n".join(lines)


def split(message: str, limit: int = MAX_MESSAGE) -> list[str]:
    """줄 단위로 텔레그램 길이 제한에 맞춰 나눈다."""
    chunks: list[str] = []
    current = ""
    for line in message.split("\n"):
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
