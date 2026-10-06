# 테슬라 데일리 뉴스 브리핑

매일 아침 **09:00 KST**에 테슬라 관련 뉴스·애널리스트 의견·투자자 여론을
한 번에 모아 텔레그램으로 보내줍니다.

## 무엇을 모으나

| 소스 | 내용 |
|---|---|
| Google News RSS (영문 4개 쿼리 · 한글 2개 쿼리) | 주가/애널리스트/머스크/실적 관련 전체 매체 |
| Yahoo Finance TSLA | 종목 헤드라인 |
| Seeking Alpha TSLA | 투자 분석 아티클 |
| Electrek · Teslarati · InsideEVs · CleanTechnica | 테슬라 전문 매체 |
| r/teslainvestorsclub · r/TeslaMotors · r/stocks | 개인 투자자 여론 |
| Yahoo Finance / stooq | TSLA 시세 (전일 대비 등락) |

## 브리핑 구성

### 같은 사건은 한 줄로

같은 사건을 여러 매체가 받아쓰면 제목만 조금씩 다른 기사가 수십 건 쌓입니다.
그래서 **한 섹터 안에서 같은 주제의 기사는 한 줄로 합치고**, 대표 기사 하나와
`+N개 매체`만 보여줍니다. 주제는 `TOPICS`에 손으로 추려둔 목록입니다.

> 제목 유사도(문자 2-gram Jaccard)로 '같은 사건'을 자동 판별하는 방법도
> 실제 기사로 재봤는데, 같은 사건과 다른 사건의 경계가 0.05밖에 안 벌어져
> 실데이터에서 오인식이 납니다. 손으로 추린 주제 목록이 결정적이고 왜 묶였는지
> 설명도 됩니다.

합치기는 **섹터 안에서만** 합니다. 주제만으로 전체를 묶으면 그날 지배적인 주제
하나가 실적·목표주가 기사까지 전부 빨아들입니다. 같은 사이버캡 소식이라도
규제 기사와 실적 기사는 따로 남습니다.

### 주요 기사 먼저

정렬 기준은 **몇 개 매체가 다뤘는지**입니다. 여러 매체가 동시에 받아썼다는 것
자체가 그날 무엇이 중요했는지 알려주는 신호입니다. 그다음이 한국어, 그다음이
최신순입니다.

맨 위 **오늘의 핵심**은 그중 상위 3개를 섹터 이름과 함께 보여줍니다
(최소 3개 매체가 다룬 묶음만). 여기에 올라간 묶음은 **아래 섹터 목록에서
빠지므로** 같은 기사를 두 번 읽지 않습니다.

그 아래로 카테고리별 기사가 **카테고리당 4건**씩 붙습니다. 각 카테고리 안에서는
**한국어 기사를 먼저**(🇰🇷), 그다음 외신(🌐)을 최신순으로 놓습니다. 한국 매체가
전체의 절반 가까이 되므로 대부분의 소식은 한국어로 먼저 읽게 됩니다. 번역기는
쓰지 않습니다 — 외신 제목은 원문 그대로입니다.

수집한 기사는 최근 24시간 내로 거르고, 스팸을 걷어낸 뒤, 제목이 같은
중복 기사를 합쳐 6개 카테고리로 나눠 보냅니다.

걸러내는 스팸은 두 종류입니다.

- **기관 지분공시(13F) 자동 생성 기사** — `Makes New Investment in Tesla`,
  `Shares Sold by …`, `Acquires 12,500 Shares of …` 같은 템플릿 제목. MarketBeat
  계열이 매일 수십 건씩 찍어냅니다.
- **콘텐츠팜·가십 매체** — 머스크 연애사, 바이럴 영상 요약 같은 기사

실적 발표, 인수 소식, `Ark Invest sells $110 million in Tesla stock` 같은 실제
기관 매매 뉴스는 걸러지지 않습니다(테스트로 고정해 두었습니다).

- 🎯 애널리스트·투자의견 (목표주가, 등급 상하향, 커버리지 개시)
- 💰 실적·재무 (인도량, 매출, 마진, 가이던스)
- 📈 주가·시장 (급등락, 공매도, 옵션, 시총)
- ⚖️ 규제·리스크 (리콜, NHTSA/SEC 조사, 소송, 관세)
- 🔧 제품·기술 (FSD, 로보택시, 옵티머스, 배터리, 신차)
- 🗣 투자자 커뮤니티 여론

## 설정 (5분)

### 1. 텔레그램 봇 만들기

1. 텔레그램에서 [@BotFather](https://t.me/BotFather)에게 `/newbot` 전송 → 이름 지정
2. 받은 **봇 토큰** (`1234567890:AAE...`) 보관
3. 만든 봇과 대화를 시작하고 아무 메시지나 한 번 전송 (봇은 먼저 말을 걸 수 없음)
4. 브라우저에서 아래 주소를 열어 `chat.id` 확인

   ```
   https://api.telegram.org/bot<봇토큰>/getUpdates
   ```

### 2. GitHub Secrets 등록

저장소 → **Settings → Secrets and variables → Actions → New repository secret**

| 이름 | 값 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather가 준 토큰 |
| `TELEGRAM_CHAT_ID` | 위에서 확인한 `chat.id` |

### 3. 동작 확인

**Actions → 테슬라 데일리 뉴스 → Run workflow**로 즉시 한 번 실행해 보세요.
`dry_run`을 켜면 전송 없이 로그로만 결과를 확인할 수 있습니다.

이후로는 매일 09:00 KST에 자동 실행됩니다.

## 로컬 실행

```bash
pip install -r requirements.txt

python -m tesla_news --dry-run          # 전송 없이 출력만
python -m tesla_news --hours 48         # 최근 48시간으로 범위 확대

TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python -m tesla_news
```

## 테스트

```bash
pip install pytest
python -m pytest tests -q
```

## 알아둘 점

- GitHub Actions의 `schedule`은 러너 혼잡도에 따라 **수 분에서 길게는 30분 정도 지연**될 수 있습니다. 정시 도착이 꼭 필요하면 cron을 `50 23 * * *`처럼 조금 앞당겨 두세요.
- 공개 저장소의 예약 워크플로는 **60일간 저장소 활동이 없으면 자동 비활성화**됩니다. 알림이 끊기면 Actions 탭에서 다시 켜면 됩니다.
- 일부 소스(Seeking Alpha, Reddit, Yahoo)는 데이터센터 IP에 `429`를 돌려주는 경우가 있습니다. 실패한 소스는 로그에 `[warn]`으로 남고 나머지 소스로 브리핑은 정상 발송됩니다. 시세도 마찬가지로, 세 곳(Yahoo 2개 호스트 → stooq)을 모두 실패하면 시세 줄만 빠지고 뉴스는 그대로 갑니다.
- 텔레그램 전송이 실패하면 워크플로가 실패로 끝나고, 로그에 텔레그램이 돌려준 사유가 그대로 남습니다. `chat not found`는 `TELEGRAM_CHAT_ID`가 틀린 것이고, `bot can't initiate conversation`은 봇에게 먼저 말을 걸지 않은 것입니다. 브라우저에서 `https://api.telegram.org/bot<토큰>/sendMessage?chat_id=<chat_id>&text=test`를 열어보면 같은 사유를 바로 확인할 수 있습니다.
- 카카오톡은 제외했습니다. 카카오 API로 자동 발송하려면 사업자 등록 + 채널 심사가 필요하고, 심사 없이 쓸 수 있는 "나에게 보내기"도 토큰을 주기적으로 갱신해야 해서 무인 자동화에 적합하지 않습니다.

## 손보기 좋은 곳

- 소스 추가/제거 → `tesla_news/feeds.py`의 `SOURCES`
- 스팸 필터 → `tesla_news/feeds.py`의 `SPAM_TITLE`(제목 패턴), `SPAM_SOURCE`(매체 이름).
  거슬리는 매체가 새로 보이면 `SPAM_SOURCE`에 이름 한 조각만 추가하면 됩니다
- 카테고리 분류 키워드 → `tesla_news/report.py`의 `CATEGORIES`
- 카테고리당 표시 개수 → `report.MAX_PER_CATEGORY` (기본 5건)
- 「오늘의 핵심」 주제 목록 → `tesla_news/report.py`의 `TOPICS`. 관심 주제를
  추가하면 그날 그 주제가 몇 건 보도됐는지 바로 잡힙니다
- 발송 시각 → `.github/workflows/tesla-news-daily.yml`의 `cron` (UTC 기준)
