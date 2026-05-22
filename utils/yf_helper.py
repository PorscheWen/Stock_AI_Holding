"""
Yahoo Finance rate-limit-aware helper.
Provides TTL in-memory cache and exponential-backoff retry so no caller
needs to manage delays or retries by itself.
"""
from __future__ import annotations

import logging
import time
from threading import Lock
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)

# Cache: symbol -> (fetched_at_timestamp, info_dict)
_INFO_CACHE: dict[str, tuple[float, dict]] = {}
_INFO_CACHE_LOCK = Lock()
INFO_CACHE_TTL = 300  # 5 minutes

# Retry schedule for rate-limit errors (seconds to wait before each retry)
_RETRY_DELAYS = (3.0, 8.0, 20.0)

# Minimum gap between consecutive Yahoo requests (shared across all calls)
_INTER_REQUEST_DELAY = 1.2  # seconds
_last_request_at: float = 0.0
_throttle_lock = Lock()


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "429" in msg
        or "too many requests" in msg
        or "rate limit" in msg
        or "ratelimit" in msg
    )


def _throttle() -> None:
    """Block until the minimum inter-request gap has elapsed."""
    global _last_request_at
    with _throttle_lock:
        wait = _INTER_REQUEST_DELAY - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def get_ticker_info(symbol: str, use_cache: bool = True) -> dict[str, Any]:
    """
    Return yf.Ticker(symbol).info with:
    - TTL in-memory cache (5 min)
    - Per-request throttle (1.2 s gap)
    - Exponential-backoff retry on HTTP 429 / rate-limit errors
    """
    sym = symbol.strip().upper()
    if use_cache:
        with _INFO_CACHE_LOCK:
            entry = _INFO_CACHE.get(sym)
            if entry and (time.time() - entry[0]) < INFO_CACHE_TTL:
                return entry[1]

    last_exc: Exception | None = None
    for attempt, delay in enumerate([0.0, *_RETRY_DELAYS]):
        if delay > 0:
            logger.warning(
                "[yf_helper] rate-limit on %s – waiting %.0fs (retry %d/%d)",
                sym, delay, attempt, len(_RETRY_DELAYS),
            )
            time.sleep(delay)
        try:
            _throttle()
            info: dict[str, Any] = yf.Ticker(sym).info or {}
            with _INFO_CACHE_LOCK:
                _INFO_CACHE[sym] = (time.time(), info)
            return info
        except Exception as exc:
            last_exc = exc
            if not _is_rate_limit(exc):
                raise

    logger.error("[yf_helper] all retries exhausted for %s: %s", sym, last_exc)
    raise last_exc  # type: ignore[misc]


def get_ticker_with_history(
    symbol: str, period: str = "4mo"
) -> tuple[yf.Ticker, Any]:
    """
    Return (Ticker, history_df) with throttle + retry on rate-limit errors.
    The ticker's .info is NOT cached here (use get_ticker_info for that).
    """
    sym = symbol.strip().upper()
    last_exc: Exception | None = None
    for attempt, delay in enumerate([0.0, *_RETRY_DELAYS]):
        if delay > 0:
            logger.warning(
                "[yf_helper] rate-limit on %s history – waiting %.0fs (retry %d/%d)",
                sym, delay, attempt, len(_RETRY_DELAYS),
            )
            time.sleep(delay)
        try:
            _throttle()
            t = yf.Ticker(sym)
            hist = t.history(period=period)
            return t, hist
        except Exception as exc:
            last_exc = exc
            if not _is_rate_limit(exc):
                raise

    logger.error("[yf_helper] all retries exhausted (history) for %s: %s", sym, last_exc)
    raise last_exc  # type: ignore[misc]


def invalidate_cache(symbol: str | None = None) -> None:
    """Remove one symbol (or all) from the info cache."""
    with _INFO_CACHE_LOCK:
        if symbol is None:
            _INFO_CACHE.clear()
        else:
            _INFO_CACHE.pop(symbol.strip().upper(), None)
