"""
台／美股顯示名稱：台股優先中文（證交所查詢、FinMind 備援），並尊重使用者已儲存的中文名稱。
"""
from __future__ import annotations

import re
from typing import Any

import requests

_TWSE_CODE_QUERY = "https://www.twse.com.tw/rwd/zh/api/codeQuery"
_FINMIND_INFO = "https://api.finmindtrade.com/api/v4/data"


def _has_cjk(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))


def _taiwan_numeric_id(symbol: str) -> tuple[str | None, str | None]:
    """回傳 (數字代號, 後綴 'TW'|'TWO'|None)。"""
    s = symbol.strip().upper()
    m = re.match(r"^(\d{4,6})\.(TW|TWO)$", s)
    if m:
        return m.group(1), m.group(2)
    if re.fullmatch(r"\d{4,6}", s):
        return s, "TW"
    return None, None


def fetch_twse_zh_name(stock_code: str, timeout: float = 8.0) -> str | None:
    try:
        r = requests.get(_TWSE_CODE_QUERY, params={"query": stock_code}, timeout=timeout)
        r.encoding = "utf-8"
        j: dict[str, Any] = r.json()
        suggestions = j.get("suggestions") or []
        if not suggestions or not isinstance(suggestions, list):
            return None
        first = suggestions[0]
        if not isinstance(first, str):
            return None
        if first.startswith("("):
            return None
        if "\t" not in first:
            return None
        _, zh = first.split("\t", 1)
        zh = zh.strip()
        return zh or None
    except Exception:
        return None


def fetch_finmind_stock_name_zh(stock_id: str, timeout: float = 12.0) -> str | None:
    try:
        r = requests.get(
            _FINMIND_INFO,
            params={"dataset": "TaiwanStockInfo", "data_id": stock_id},
            timeout=timeout,
        )
        r.raise_for_status()
        j = r.json()
        data = j.get("data") or []
        if not data or not isinstance(data, list):
            return None
        row0 = data[0]
        if not isinstance(row0, dict):
            return None
        name = str(row0.get("stock_name") or "").strip()
        return name or None
    except Exception:
        return None


def resolve_stock_name_zh(
    symbol: str,
    *,
    yf_info: dict[str, Any] | None = None,
    stored_name: str = "",
) -> str:
    """
    顯示用股票名稱：已存中文 > 台股中文對照 > Yahoo Finance 欄位 > 代碼。
    """
    sym = symbol.strip()
    stored = (stored_name or "").strip()
    if _has_cjk(stored):
        return stored

    tid, suffix = _taiwan_numeric_id(sym)
    if tid:
        if suffix == "TWO" or sym.upper().endswith(".TWO"):
            zh = fetch_finmind_stock_name_zh(tid) or fetch_twse_zh_name(tid)
        else:
            zh = fetch_twse_zh_name(tid) or fetch_finmind_stock_name_zh(tid)
        if zh:
            return zh

    if yf_info:
        cand = str(yf_info.get("shortName") or yf_info.get("longName") or "").strip()
        if cand:
            return cand
    return sym
