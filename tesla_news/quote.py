"""TSLA 시세 조회. 야후가 막히는 경우가 잦아 stooq로 폴백한다."""

from __future__ import annotations

from dataclasses import dataclass

import requests

from .feeds import TIMEOUT, USER_AGENT


@dataclass
class Quote:
    price: float
    previous_close: float
    source: str

    @property
    def change(self) -> float:
        return self.price - self.previous_close

    @property
    def change_pct(self) -> float:
        return self.change / self.previous_close * 100


def _from_yahoo() -> Quote:
    response = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/TSLA?range=1d&interval=1d",
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    meta = response.json()["chart"]["result"][0]["meta"]
    return Quote(
        price=float(meta["regularMarketPrice"]),
        previous_close=float(meta.get("chartPreviousClose") or meta["previousClose"]),
        source="Yahoo Finance",
    )


def _from_stooq() -> Quote:
    response = requests.get(
        "https://stooq.com/q/l/?s=tsla.us&f=sd2t2ohlc&h&e=csv",
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    header, row = response.text.strip().splitlines()[:2]
    fields = dict(zip(header.split(","), row.split(",")))
    return Quote(
        price=float(fields["Close"]),
        previous_close=float(fields["Open"]),
        source="stooq (종가/시가 기준)",
    )


def fetch() -> Quote | None:
    for provider in (_from_yahoo, _from_stooq):
        try:
            return provider()
        except (requests.RequestException, KeyError, ValueError, IndexError) as exc:
            print(f"[warn] 시세 조회 실패 ({provider.__name__}): {exc}")
    return None
