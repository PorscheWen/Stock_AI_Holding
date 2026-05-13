"""
台股大盤／指標一個月展望（Agent 推論 + 公開行情摘要）
以加權指數、0050 等公開資料為輸入，產出結構化 JSON；無 API Key 時改為純規則摘要。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic
import yfinance as yf

from config.settings import ANTHROPIC_AUTH_TOKEN, CLAUDE_MODEL

logger = logging.getLogger(__name__)

TW_INDEX_SYMBOLS = ("^TWII", "0050.TW")


def _rsi_series(close, period: int = 14) -> float | None:
    try:
        import pandas as pd

        delta = close.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        v = float(rsi.iloc[-1])
        if v != v:
            return None
        return round(v, 1)
    except Exception:
        return None


def _ret_pct(close, bars: int) -> float | None:
    try:
        if len(close) < bars + 1:
            return None
        a = float(close.iloc[-bars - 1])
        b = float(close.iloc[-1])
        if a == 0:
            return None
        return round((b - a) / a * 100.0, 2)
    except Exception:
        return None


def build_taiwan_market_snapshot() -> dict[str, Any]:
    """擷取台股大盤／0050 近期報酬與 RSI，供 Agent 與規則摘要使用。"""
    indices: dict[str, Any] = {}
    for sym in TW_INDEX_SYMBOLS:
        row: dict[str, Any] = {"symbol": sym, "ok": False}
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="4mo")
            if hist is None or hist.empty:
                indices[sym] = row
                continue
            close = hist["Close"].astype(float)
            last = float(close.iloc[-1])
            last_date = str(hist.index[-1])[:10]
            row.update({
                "ok": True,
                "last_close": round(last, 4),
                "last_bar_date": last_date,
                "ret_5d_pct": _ret_pct(close, 5),
                "ret_20d_pct": _ret_pct(close, 20),
                "ret_60d_pct": _ret_pct(close, 60),
                "rsi_14": _rsi_series(close, 14),
            })
        except Exception as e:
            logger.debug("snapshot %s: %s", sym, e)
        indices[sym] = row

    primary = indices.get("0050.TW") or {}
    bias = "neutral"
    if primary.get("ok"):
        r20 = primary.get("ret_20d_pct")
        if r20 is not None:
            if r20 >= 3.0:
                bias = "up"
            elif r20 <= -3.0:
                bias = "down"
            elif r20 >= 1.0:
                bias = "up"
            elif r20 <= -1.0:
                bias = "down"

    return {"indices": indices, "rule_bias": bias, "as_of": primary.get("last_bar_date")}


def _heuristic_outlook(snapshot: dict[str, Any]) -> dict[str, Any]:
    b = snapshot.get("rule_bias") or "neutral"
    label = {"up": "偏多", "down": "偏空", "neutral": "中性整理"}.get(b, "中性整理")
    tw50 = (snapshot.get("indices") or {}).get("0050.TW") or {}
    twii = (snapshot.get("indices") or {}).get("^TWII") or {}
    parts = []
    if tw50.get("ok"):
        parts.append(
            f"0050 近20日報酬約 {tw50.get('ret_20d_pct')}%　RSI {tw50.get('rsi_14')}"
        )
    if twii.get("ok"):
        parts.append(
            f"加權指數近20日報酬約 {twii.get('ret_20d_pct')}%　RSI {twii.get('rsi_14')}"
        )
    summary = "；".join(parts) if parts else "公開行情資料不足，僅能做中性假設。"
    return {
        "bias_one_month": b,
        "bias_label_zh": label,
        "one_month_summary_zh": f"依最近價量結構，未來約一個月大盤基調判為「{label}」。{summary}（僅為情境推估，非投資要約。）",
        "key_watchpoints_zh": [
            "量能是否持續配合趨勢",
            "國際利率與匯率對資金面的影響",
            "重要指數關鍵價突破或跌破後的追價／停損紀律",
        ],
        "confidence_0_to_1": 0.45,
        "source": "rule_heuristic",
    }


SYSTEM = """你是專業台股策略助理。使用者會提供加權指數（^TWII）與台股 0050（0050.TW）的公開行情摘要（報酬率、RSI、最近收盤日）。
請根據這些數據，**推估未來約一個月** 台股大盤可能情境（不是保證報酬）。

必須只輸出一段合法 JSON（不要 markdown、不要說明文字），格式：
{
  "bias_one_month": "up" | "down" | "neutral",
  "bias_label_zh": "偏多|偏空|中性整理 擇一",
  "one_month_summary_zh": "80～200 字繁體中文，說明為何如此判斷與可能路徑",
  "key_watchpoints_zh": ["2～4 條繁中重點觀察"],
  "confidence_0_to_1": 0.0 到 1 的小數
}

注意：
- 語氣為參考與教育用途，避免「保證上漲／必跌」等字眼。
- 若資料明顯不足，bias_one_month 用 neutral，confidence 偏低。"""


def _parse_json_obj(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]+\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


def run_one_month_tw_outlook(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    產出台股約一個月展望。有 Anthropic Key 時由模型推論；否則使用規則摘要。
    回傳 dict 會併入 advisor report 的 tw_market_outlook。
    """
    snap = snapshot if snapshot is not None else build_taiwan_market_snapshot()
    if not (ANTHROPIC_AUTH_TOKEN or "").strip():
        h = _heuristic_outlook(snap)
        h["snapshot"] = snap
        return h

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_AUTH_TOKEN)
        user_text = json.dumps(snap, ensure_ascii=False, indent=2)
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1200,
            system=SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": f"行情摘要如下，請輸出 JSON：\n{user_text}"}],
                }
            ],
        )
        raw = msg.content[0].text.strip()
        data = _parse_json_obj(raw)
        if not isinstance(data, dict):
            raise ValueError("invalid json from model")
        bias = str(data.get("bias_one_month", "neutral")).lower()
        if bias not in ("up", "down", "neutral"):
            bias = "neutral"
        data["bias_one_month"] = bias
        data["source"] = "claude"
        data["snapshot"] = snap
        data["raw_model"] = raw[:2000]
        return data
    except Exception as e:
        logger.warning("tw_market_agent Claude 失敗，改 heuristic: %s", e)
        h = _heuristic_outlook(snap)
        h["snapshot"] = snap
        h["model_error"] = str(e)
        return h
