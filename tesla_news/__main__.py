"""테슬라 뉴스를 모아 텔레그램으로 보낸다.

사용법:
    python -m tesla_news              # 수집 후 텔레그램 전송
    python -m tesla_news --dry-run    # 전송 없이 표준출력으로 확인
"""

from __future__ import annotations

import argparse

from . import feeds, quote, report, telegram


def main() -> None:
    parser = argparse.ArgumentParser(description="테슬라 데일리 뉴스 브리핑")
    parser.add_argument("--hours", type=int, default=24, help="수집 기간 (기본 24시간)")
    parser.add_argument("--dry-run", action="store_true", help="전송하지 않고 출력만")
    args = parser.parse_args()

    articles = feeds.collect(hours=args.hours)
    message = report.build(articles, quote.fetch())
    chunks = report.split(message)

    if args.dry_run:
        print(message)
        print(f"\n--- 기사 {len(articles)}건, 메시지 {len(chunks)}개 ---")
        return

    telegram.send(chunks)
    print(f"전송 완료: 기사 {len(articles)}건, 메시지 {len(chunks)}개")


if __name__ == "__main__":
    main()
