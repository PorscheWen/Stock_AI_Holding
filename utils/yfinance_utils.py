"""
Yahoo Finance API helpers:
  - Rate-limit error detection
  - Retry with exponential back-off for .info and .history()
  - Lightweight TTL cache for .info so advisor + prices endpoint share results
"""
from __future__ import annotations

import logging
import time
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)

# ── rate-limit keyword matching ──────────────────────────────────────────────
_RATE_LIMIT_TOKENS = (
    "429",
    "too many requests",
    "rate limit",
    "ratelimit",
    "throttle",
    "exceeded",
)


def is_rate_limit_error(exc: Exception) -> bool:
    """Return True when the exception looks like a Yahoo Finance 429 / rate-limit."""
    msg = str(exc).lower()
    return any(t in msg for t in _RATE_LIMIT_TOKENS)


# ── TTL in-memory cache for Ticker.info ─────────────────────────────────────
# Keyed by symbol → (expiry_timestamp, info_dict)
_info_cache: dict[str, tuple[float, dict[str, Any]]] = {}

#: How long (seconds) a cached .info result is considered fresh.
CACHE_TTL: int = 300  # 5 minutes


def _cache_get(symbol: str) -> dict[str, Any] | None:
    entry = _info_cache.get(symbol.upper())
    if entry and time.time() < entry[0]:
        return entry[1]
    return None


def _cache_set(symbol: str, info: dict[str, Any]) -> None:
    _info_cache[symbol.upper()] = (time.time() + CACHE_TTL, info)


def cache_invalidate(symbol: str) -> None:
    """Remove a cached entry (e.g. after a known stale result)."""
    _info_cache.pop(symbol.upper(), None)


# ── retry helpers ─────────────────────────────────────────────────────────────

def yf_info_with_retry(
    symbol: str,
    *,
    max_retries: int = 3,
    base_delay: float = 5.0,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Fetch yf.Ticker(symbol).info with:
      - TTL cache (5 min by default)
      - Exponential back-off on rate-limit errors (5s, 10s, 20s …)

    Always returns a dict — never raises — so callers can treat missing
    data gracefully.
    """
    if use_cache:
        cached = _cache_get(symbol)
        if cached is not None:
            logger.debug("yf_info cache hit: %s", symbol)
            return cached

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            info = yf.Ticker(symbol).info or {}
            if use_cache and info:
                _cache_set(symbol, info)
            return info
        except Exception as exc:
            last_exc = exc
            if is_rate_limit_error(exc):
                wait = base_delay * (2 ** attempt)
                logger.warning(
                    "[yf_info] rate-limit on %s (attempt %d/%d), retrying in %.0fs",
                    symbol, attempt + 1, max_retries + 1, wait,
                )
                time.sleep(wait)
            else:
                logger.debug("yf_info %s: %s", symbol, exc)
                break  # non-rate-limit error — retry won't help

    logger.warning(
        "yf_info %s failed after %d attempt(s): %s", symbol, max_retries + 1, last_exc
    )
    return {}


def yf_history_with_retry(
    symbol: str,
    period: str = "4mo",
    *,
    max_retries: int = 3,
    base_delay: float = 5.0,
):
    """
    Fetch yf.Ticker(symbol).history(period=period) with exponential back-off.

    Returns the DataFrame on success, or None on total failure — callers
    should skip technical indicators gracefully when None is returned.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            hist = yf.Ticker(symbol).history(period=period)
            return hist
        except Exception as exc:
            last_exc = exc
            if is_rate_limit_error(exc):
                wait = base_delay * (2 ** attempt)
                logger.warning(
                    "[yf_history] rate-limit on %s (attempt %d/%d), retrying in %.0fs",
                    symbol, attempt + 1, max_retries + 1, wait,
                )
                time.sleep(wait)
            else:
                logger.debug("yf_history %s: %s", symbol, exc)
                break

    logger.warning(
        "yf_history %s failed after %d attempt(s): %s", symbol, max_retries + 1, last_exc
    )
    return None
