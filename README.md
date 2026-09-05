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

수집한 기사는 최근 24시간 내로 거르고, 제목이 같은 중복 기사를 합친 뒤
6개 카테고리로 나눠 보냅니다.

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
- 일부 소스(Seeking Alpha, Reddit)는 데이터센터 IP를 차단하는 경우가 있습니다. 실패한 소스는 로그에 `[warn]`으로 남고 나머지 소스로 브리핑은 정상 발송됩니다.
- 카카오톡은 제외했습니다. 카카오 API로 자동 발송하려면 사업자 등록 + 채널 심사가 필요하고, 심사 없이 쓸 수 있는 "나에게 보내기"도 토큰을 주기적으로 갱신해야 해서 무인 자동화에 적합하지 않습니다.

## 손보기 좋은 곳

- 소스 추가/제거 → `tesla_news/feeds.py`의 `SOURCES`
- 카테고리 분류 키워드 → `tesla_news/report.py`의 `CATEGORIES`
- 카테고리당 표시 개수 → `report.MAX_PER_CATEGORY` (기본 8건)
- 발송 시각 → `.github/workflows/tesla-news-daily.yml`의 `cron` (UTC 기준)
