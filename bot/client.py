"""
Binance Futures Testnet client wrapper.
Handles authentication (HMAC-SHA256), request signing, and HTTP communication.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger("trading_bot.client")

BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # ms


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or error body."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceClient:
    """
    Lightweight Binance Futures Testnet REST client.

    Handles:
    - HMAC-SHA256 request signing
    - Timestamp management
    - GET / POST with automatic retries on connection errors
    - Structured logging of every request and response
    """

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceClient initialised (base_url=%s)", BASE_URL)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add timestamp + HMAC-SHA256 signature to a parameter dict."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Parse response, raise BinanceAPIError on failure."""
        logger.debug(
            "HTTP %s %s → status=%d body=%s",
            response.request.method,
            response.url,
            response.status_code,
            response.text[:500],
        )
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            return {}

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            # Binance error envelope
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        response.raise_for_status()
        return data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, path: str, params: dict[str, Any] | None = None, signed: bool = False) -> Any:
        """Send a signed or unsigned GET request."""
        params = params or {}
        if signed:
            params = self._sign(params)
        url = f"{BASE_URL}{path}"
        logger.debug("GET %s params=%s", url, {k: v for k, v in params.items() if k != "signature"})
        try:
            resp = self._session.get(url, params=params, timeout=self._timeout)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error on GET %s: %s", url, exc)
            raise
        return self._handle_response(resp)

    def post(self, path: str, params: dict[str, Any] | None = None, signed: bool = True) -> Any:
        """Send a signed POST request (body as form data)."""
        params = params or {}
        if signed:
            params = self._sign(params)
        url = f"{BASE_URL}{path}"
        logger.debug(
            "POST %s params=%s",
            url,
            {k: v for k, v in params.items() if k not in ("signature", "timestamp")},
        )
        try:
            resp = self._session.post(url, data=params, timeout=self._timeout)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error on POST %s: %s", url, exc)
            raise
        return self._handle_response(resp)

    # ------------------------------------------------------------------
    # Convenience endpoints
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return True if testnet is reachable."""
        try:
            self.get("/fapi/v1/ping")
            logger.info("Ping OK — testnet is reachable.")
            return True
        except Exception as exc:
            logger.warning("Ping failed: %s", exc)
            return False

    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds."""
        data = self.get("/fapi/v1/time")
        return data["serverTime"]

    def get_account_info(self) -> dict[str, Any]:
        """Fetch futures account information."""
        return self.get("/fapi/v2/account", signed=True)

    def get_exchange_info(self, symbol: str | None = None) -> dict[str, Any]:
        """Fetch exchange info (optionally filtered by symbol)."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self.get("/fapi/v1/exchangeInfo", params=params)
