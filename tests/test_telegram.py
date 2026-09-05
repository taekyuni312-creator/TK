import pytest

from tesla_news import telegram


class FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text
        self.ok = status_code < 400


def test_failure_surfaces_telegram_description(monkeypatch):
    """텔레그램이 알려주는 실패 사유가 로그에 그대로 남아야 원인을 알 수 있다."""
    body = '{"ok":false,"error_code":400,"description":"Bad Request: chat not found"}'
    monkeypatch.setattr(telegram.requests, "post", lambda *a, **k: FakeResponse(400, body))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    with pytest.raises(RuntimeError, match="chat not found"):
        telegram.send(["hi"])


def test_success_sends_every_chunk(monkeypatch):
    sent = []
    monkeypatch.setattr(
        telegram.requests, "post",
        lambda *a, **k: sent.append(k["data"]["text"]) or FakeResponse(200, '{"ok":true}'),
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    telegram.send(["one", "two"])
    assert sent == ["one", "two"]
