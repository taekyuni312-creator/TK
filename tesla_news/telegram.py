"""텔레그램 봇 전송."""

from __future__ import annotations

import os

import requests

from .feeds import TIMEOUT


def send(chunks: list[str]) -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    for chunk in chunks:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            timeout=TIMEOUT,
            data={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            },
        )
        if not response.ok:
            # 텔레그램은 실패 사유를 응답 본문의 description 에 담아준다.
            # raise_for_status() 는 이걸 버리므로 직접 꺼내 로그에 남긴다.
            raise RuntimeError(
                f"텔레그램 전송 실패 (HTTP {response.status_code}): {response.text}"
            )
