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
        response.raise_for_status()
