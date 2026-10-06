"""수집한 기사를 카테고리별 텔레그램 메시지로 정리."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .feeds import Article
from .quote import Quote

KST = timezone(timedelta(hours=9))
WEEKDAYS = "월화수목금토일"
MAX_MESSAGE = 3800  # 텔레그램 4096자 제한 대비 여유
MAX_PER_CATEGORY = 4

KOREAN = re.compile(r"[가-힣]")

@dataclass
class Story:
    """같은 사건을 다룬 기사 묶음. 대표 하나만 보여주고 나머지는 매체 수로 센다."""

    lead: Article
    members: list[Article]

    @property
    def outlets(self) -> int:
        return len({article.source for article in self.members})

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
MIN_HIGHLIGHT_OUTLETS = 3  # 핵심에 올리려면 이만큼의 매체가 다뤄야 한다
MAX_HIGHLIGHTS = 3


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


def topic_of(article: Article) -> str | None:
    """기사가 속한 주제. TOPICS 순서가 곧 우선순위다."""
    return next((name for name, pattern in TOPICS if pattern.search(article.text)), None)


def condense(articles: list[Article]) -> list[Story]:
    """한 섹터 안에서 같은 주제의 기사를 한 줄로 합친다.

    제목 유사도로 '같은 사건'을 찾는 방법도 재봤지만, 같은 사건과 다른 사건의
    경계가 0.05밖에 안 벌어져 실제 데이터에서 오인식이 난다. 손으로 추린
    TOPICS 쪽이 결정적이고 왜 묶였는지 설명도 된다.

    묶기는 섹터 안에서만 한다. 주제만으로 전체를 묶으면 그날 지배적인 주제가
    실적·목표주가 기사까지 전부 빨아들인다.
    """
    grouped: dict[str, list[Article]] = {}
    singles: list[Story] = []
    for article in articles:
        topic = topic_of(article)
        if topic is None:
            singles.append(Story(article, [article]))
        else:
            grouped.setdefault(topic, []).append(article)
    merged = [Story(min(members, key=_reading_order), members) for members in grouped.values()]
    return sorted(merged + singles, key=_importance)


def _importance(story: Story) -> tuple:
    """많은 매체가 다룬 사건 먼저, 그다음 한국어, 그다음 최신순."""
    return (-story.outlets, not _is_korean(story.lead), -_when(story.lead))


def categorize(articles: list[Article]) -> dict[str, list[Story]]:
    """섹터로 나눈 뒤, 각 섹터 안에서 주제별로 합친다."""
    buckets: dict[str, list[Article]] = {}
    for article in articles:
        if COMMUNITY_SOURCES.search(article.source):
            name = COMMUNITY
        else:
            name = next(n for n, pattern in CATEGORIES if pattern.search(article.text))
        buckets.setdefault(name, []).append(article)
    return {name: condense(items) for name, items in buckets.items()}


def headline_stories(buckets: dict[str, list[Story]]) -> list[tuple[str, Story]]:
    """여러 매체가 동시에 다룬 묶음 순으로. 섹터 이름을 라벨로 함께 돌려준다."""
    ranked = sorted(
        ((name, story) for name, bucket in buckets.items() for story in bucket),
        key=lambda pair: _importance(pair[1]),
    )
    return [pair for pair in ranked if pair[1].outlets >= MIN_HIGHLIGHT_OUTLETS][:MAX_HIGHLIGHTS]


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


def _highlights(buckets: dict[str, list[Story]], used: set[str]) -> list[str]:
    """오늘의 핵심. 여기에 쓴 묶음은 `used`에 담아 아래 목록에서 빠지게 한다.

    라벨은 그 묶음이 속한 섹터 이름이다. 주제명을 붙이면 묶음이 여러 주제에
    걸릴 때 기사와 안 맞는 라벨이 나온다.
    """
    ranked = headline_stories(buckets)
    if not ranked:
        return []

    lines = ["📌 <b>오늘의 핵심</b>"]
    for number, (name, story) in zip("①②③", ranked):
        used.add(story.lead.url)
        lines.append(f"{number} <b>{name}</b> · {story.outlets}개 매체가 보도")
        lines.append(f"   {_link(story.lead)}")
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

    buckets = categorize(unique)
    shown: set[str] = set()
    lines += _highlights(buckets, shown)

    for name in [n for n, _ in CATEGORIES] + [COMMUNITY]:
        # 오늘의 핵심에 이미 올라간 묶음은 빼서 같은 기사를 두 번 읽지 않게 한다.
        bucket = [s for s in buckets.get(name, []) if s.lead.url not in shown]
        if not bucket:
            continue
        lines.append(f"<b>{name}</b> ({len(bucket)}건)")
        for story in bucket[:MAX_PER_CATEGORY]:
            lead = story.lead
            flag = "🇰🇷" if _is_korean(lead) else "🌐"
            meta = f"{html.escape(lead.source, quote=False)} · {_ago(lead.published, now)}"
            if story.outlets > 1:
                meta += f" · <b>+{story.outlets - 1}개 매체</b>"
            lines.append(f"{flag} {_link(lead)}\n     <i>{meta}</i>")
        if len(bucket) > MAX_PER_CATEGORY:
            lines.append(f"     <i>… 외 {len(bucket) - MAX_PER_CATEGORY}건</i>")
        lines.append("")

    issues = sum(len(bucket) for bucket in buckets.values())
    lines.append(f"{issues}개 이슈 · 기사 {len(unique)}건")
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
