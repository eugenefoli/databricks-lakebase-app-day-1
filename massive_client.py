"""
Client for the Massive API.

The API key is stored in a Databricks secret scope (see setup_secrets.py) and
resolved at runtime via the Databricks SDK - it is never stored in code, env
files, or app.yaml.
"""

import base64
import os
from typing import Any

import requests
from databricks.sdk import WorkspaceClient

_w = WorkspaceClient()

_SCOPE = os.environ.get("MASSIVE_SECRET_SCOPE", "massive")
_KEY = os.environ.get("MASSIVE_SECRET_KEY", "api-key")
_BASE_URL = os.environ.get("MASSIVE_API_BASE_URL", "https://api.massive.com")

_DEFAULT_TIMEOUT = 30


def _get_api_key() -> str:
    """Fetch and decode the Massive API key from the Databricks secret scope."""
    secret = _w.secrets.get_secret(scope=_SCOPE, key=_KEY)
    return base64.b64decode(secret.value).decode("utf-8")


class MassiveClient:
    """Thin wrapper around the Massive API with auth + retry-friendly session."""

    def __init__(self, base_url: str | None = None, timeout: int = _DEFAULT_TIMEOUT):
        self.base_url = (base_url or _BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {_get_api_key()}",
                "Content-Type": "application/json",
            }
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = self._session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        resp = self._session.post(f"{self.base_url}{path}", json=json, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def paginated_get(self, path: str, params: dict[str, Any] | None = None, page_size: int = 200):
        """
        Generator that yields items across all pages of a "massive" (large)
        paginated dataset. Assumes a cursor-based API shape:
        {"items": [...], "next_cursor": "..." | null}
        Adjust to match the real Massive API pagination contract.
        """
        cursor = None
        params = dict(params or {})
        params["page_size"] = page_size

        while True:
            if cursor:
                params["cursor"] = cursor
            data = self.get(path, params=params)
            items = data.get("items", [])
            for item in items:
                yield item

            cursor = data.get("next_cursor")
            if not cursor:
                break

    def get_latest_price(self, symbol: str) -> dict:
        """
        Fetch the latest traded price for a single symbol in a SINGLE API
        call (no pagination). Use this instead of paginated_get() whenever
        the caller needs to stay within tight API rate limits (e.g.
        classroom/student accounts), at the cost of only being able to
        request one symbol per request.
        """
        data = self.get(f"/v2/aggs/ticker/{symbol}/prev")
        return data

    def get_aggregates(self, symbol: str, from_date: str, to_date: str, timespan: str = "day") -> dict:
        """
        Fetch historical OHLCV aggregates (bars) for technical analysis.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            timespan: Bar size - 'day', 'week', or 'month'. Default: 'day'

        Returns:
            {
                "ticker": "AAPL",
                "queryCount": 50,
                "resultsCount": 50,
                "adjusted": true,
                "results": [
                    {
                        "v": 100000000,  # volume
                        "vw": 150.25,    # volume-weighted average
                        "o": 149.50,     # open
                        "c": 151.20,     # close
                        "h": 152.00,     # high
                        "l": 149.00,     # low
                        "t": 1609459200000,  # timestamp (ms)
                        "n": 500000      # number of transactions
                    },
                    ...
                ]
            }

        Example:
            client = MassiveClient()
            data = client.get_aggregates('AAPL', '2024-01-01', '2024-03-01')
            closes = [bar['c'] for bar in data.get('results', [])]
        """
        path = f"/v2/aggs/ticker/{symbol}/range/1/{timespan}/{from_date}/{to_date}"
        params = {"adjusted": "true", "sort": "asc"}
        data = self.get(path, params=params)
        return data

    def get_ticker_details(self, symbol: str) -> dict:
        """
        Fetch company fundamentals and metadata for a stock ticker.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            {
                "results": {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "market": "stocks",
                    "locale": "us",
                    "primary_exchange": "XNAS",
                    "type": "CS",
                    "active": true,
                    "currency_name": "usd",
                    "cik": "0000320193",
                    "composite_figi": "BBG000B9XRY4",
                    "share_class_figi": "BBG001S5N8V8",
                    "market_cap": 2500000000000,
                    "phone_number": "...",
                    "address": {...},
                    "description": "Apple Inc. designs, manufactures...",
                    "sic_code": "3571",
                    "sic_description": "Electronic Computers",
                    "ticker_root": "AAPL",
                    "homepage_url": "https://www.apple.com",
                    "total_employees": 164000,
                    "list_date": "1980-12-12",
                    "branding": {...},
                    "share_class_shares_outstanding": 15000000000,
                    "weighted_shares_outstanding": 15000000000,
                    "round_lot": 100
                },
                "status": "OK"
            }

        Example:
            client = MassiveClient()
            data = client.get_ticker_details('AAPL')
            market_cap = data.get('results', {}).get('market_cap')
        """
        path = f"/v3/reference/tickers/{symbol}"
        data = self.get(path)
        return data
