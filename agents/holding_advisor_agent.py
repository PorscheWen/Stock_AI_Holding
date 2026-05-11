"""
Holding PWA — Agent 操作建議
股價以公開金融 API 取得並交叉確認：
  - 主來源：Yahoo Finance（yfinance，公開行情）
  - 輔助確認：Stooq 日線 CSV（無需 API Key，僅作價差檢核）

每筆報告含建議日期、各檔建議內文與整份 advice_content，供 advisor_store 持久化。
"""
from __future__ import annotations

import logging
import urllib.request
from datetime import datetime, timezone
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)

QUOTE_PROVIDER_PRIMARY = "Yahoo Finance（yfinance 公開 API）"
QUOTE_PROVIDER_CROSS = "Stooq（日線 CSV 公開資料）"


def _stooq_symbol(sym: str) -> str | None:
    u = sym.strip().upper()
    if u.endswith(".TW"):
        return u.replace(".TW", ".tw").lower()
    if "." in u and not u.endswith(".TW"):
        return None
    return f"{u.lower()}.us"


def _stooq_last_close(symbol: str) -> tuple[float | None, str | None]:
    """回傳 (收盤價, 該筆資料日期 YYYY-MM-DD)。"""
    code = _stooq_symbol(symbol)
    if not code:
        return None, None
    url = f"https://stooq.com/q/d/l/?s={code}&i=d"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            text = resp.read().decode("utf-8", errors="replace").strip()
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if len(lines) < 2:
            return None, None
        parts = lines[-1].split(",")
        if len(parts) < 5:
            return None, None
        bar_date, close_s = parts[0], parts[4]
        return float(close_s), bar_date
    except Exception as e:
        logger.debug("stooq %s: %s", symbol, e)
        return None, None


def _yahoo_price_and_bar(ticker: yf.Ticker, hist) -> tuple[float | None, str | None, str | None]:
    """
    優先使用 Yahoo 即時欄位，否則用日線最後收盤。
    回傳 (價格, K 棒日期字串, currency)
    """
    info = ticker.info or {}
    cur = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("postMarketPrice")
    if cur is not None:
        try:
            lp = float(cur)
            md = info.get("regularMarketTime") or info.get("postMarketTime")
            bar_d = None
            if md:
                try:
                    bar_d = datetime.fromtimestamp(
                        int(md), tz=timezone.utc
                    ).strftime("%Y-%m-%d %H:%M UTC")
                except (TypeError, ValueError, OSError):
                    bar_d = None
            ccy = info.get("currency")
            return lp, bar_d, str(ccy) if ccy else None
        except (TypeError, ValueError):
            pass

    if hist is None or hist.empty:
        return None, None, None
    close_s = hist["Close"].astype(float)
    last = float(close_s.iloc[-1])
    ts = hist.index[-1]
    try:
        bar_d = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
    except Exception:
        bar_d = str(ts)[:10]
    ccy = info.get("currency")
    return last, bar_d, str(ccy) if ccy else None


def _rsi(close, period: int = 14) -> float | None:
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


def _analyze_one(
    symbol: str,
    shares: float,
    avg_price: float,
    note: str,
    quote_fetched_at: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "symbol": symbol,
        "shares": shares,
        "avg_price": avg_price,
        "note": note or "",
        "name": symbol,
        "last_price": None,
        "current_price": None,
        "pnl_amount": None,
        "pnl_pct": None,
        "rsi": None,
        "volume_ratio": None,
        "suggestion": "",
        "stop_hint": None,
        "horizon": "波段",
        "quote_provider": QUOTE_PROVIDER_PRIMARY,
        "quote_cross_check": None,
        "quote_bar_date": None,
        "quote_fetched_at": quote_fetched_at,
        "price_cross_ok": None,
        "currency": None,
    }
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        name = info.get("shortName") or info.get("longName") or symbol
        row["name"] = str(name)

        hist = t.history(period="4mo")
        yahoo_ref, y_bar, ccy = _yahoo_price_and_bar(t, hist)
        row["currency"] = ccy
        row["quote_bar_date"] = y_bar

        st_price, st_date = _stooq_last_close(symbol)
        if st_price is not None:
            row["quote_cross_check"] = {
                "provider": QUOTE_PROVIDER_CROSS,
                "close": round(st_price, 4),
                "bar_date": st_date,
            }

        price = yahoo_ref
        if price is None and st_price is not None:
            price = st_price
            row["quote_provider"] = f"{QUOTE_PROVIDER_PRIMARY}（即時欄位缺，改採日線／輔助來源）"

        if price is None:
            row["suggestion"] = "無法自公開 API 取得有效股價，請稍後再試或確認代碼。"
            row["advice_content"] = _stock_advice_text(row)
            return row

        row["last_price"] = round(price, 4)
        row["current_price"] = row["last_price"]

        if yahoo_ref is not None and st_price is not None and yahoo_ref > 0:
            diff_pct = abs(yahoo_ref - st_price) / yahoo_ref * 100.0
            row["price_cross_ok"] = diff_pct <= 2.5
            if not row["price_cross_ok"]:
                row["suggestion"] = (
                    f"Yahoo 與 Stooq 收盤參考價差約 {diff_pct:.2f}%，請以券商成交為準。"
                )

        if hist is None or hist.empty:
            row["volume_ratio"] = None
            row["rsi"] = None
        else:
            close_s = hist["Close"].astype(float)
            vol = hist["Volume"].astype(float)
            v_last = float(vol.iloc[-1])
            v_avg = float(vol.iloc[-20:].mean()) if len(vol) >= 5 else v_last
            row["volume_ratio"] = round(v_last / v_avg, 2) if v_avg > 0 else None
            row["rsi"] = _rsi(close_s)

        if shares and avg_price and avg_price > 0:
            row["pnl_amount"] = round((price - avg_price) * shares, 2)
            row["pnl_pct"] = round((price - avg_price) / avg_price * 100.0, 2)

        stop_hint = round(price * 0.92, 4) if price else None
        row["stop_hint"] = stop_hint

        parts: list[str] = []
        if row.get("suggestion"):
            parts.append(row["suggestion"])

        pnl_pct = row.get("pnl_pct")
        rsi = row.get("rsi")
        vr = row.get("volume_ratio") or 1.0

        if pnl_pct is not None:
            if pnl_pct >= 25:
                parts.append("獲利幅度較大，可考慮分批停利並保留核心部位。")
            elif pnl_pct >= 8:
                parts.append("目前有獲利，可續抱並上移停損／觀察關鍵價。")
            elif pnl_pct <= -12:
                parts.append("虧損已深，建議檢視是否觸及停損或基本面變化。")
            elif pnl_pct <= -5:
                parts.append("小幅虧損，嚴守停損價並避免攤平無計畫加碼。")
            else:
                parts.append("損益接近持平，可依關鍵價突破／跌破再調整。")

        if rsi is not None:
            if rsi >= 72:
                parts.append(f"RSI 偏高（{rsi}），短線過熱機率升。")
            elif rsi <= 32:
                parts.append(f"RSI 偏低（{rsi}），留意是否超跌反彈或弱勢延續。")

        if vr >= 1.8:
            parts.append("量能明顯放大，注意是否為趨勢延續或出貨訊號。")
        elif vr <= 0.55:
            parts.append("量能萎縮，波動可能收斂，宜等待方向。")

        if not parts:
            parts.append("技術面中性，建議維持紀律、定期檢視持股。")

        row["suggestion"] = " ".join(parts)

        if pnl_pct is not None and pnl_pct >= 15 and (rsi or 50) < 70:
            row["horizon"] = "偏短"
        elif pnl_pct is not None and pnl_pct <= -8:
            row["horizon"] = "短線檢視"
        else:
            row["horizon"] = "波段"

    except Exception as e:
        logger.warning("holding_advisor %s: %s", symbol, e)
        row["suggestion"] = f"分析失敗：{e}"

    row["advice_content"] = _stock_advice_text(row)
    return row


def _stock_advice_text(row: dict[str, Any]) -> str:
    """單檔完整建議內文（寫入 JSON 與供人閱讀）。"""
    lines = [
        f"【{row.get('name', row.get('symbol'))} {row.get('symbol')}】",
        f"建議參考價（公開 API）：{row.get('current_price') if row.get('current_price') is not None else '—'} "
        f"{row.get('currency') or ''}".strip(),
        f"報價擷取時間（伺服器）：{row.get('quote_fetched_at', '—')}",
        f"行情 K 棒日期（主來源）：{row.get('quote_bar_date') or '—'}",
        f"主來源：{row.get('quote_provider', '—')}",
    ]
    if row.get("quote_cross_check"):
        qc = row["quote_cross_check"]
        lines.append(
            f"交叉比對：{qc.get('provider')} 收盤 {qc.get('close')}（{qc.get('bar_date')}）"
            f"　價差合格：{'是' if row.get('price_cross_ok') is True else '否' if row.get('price_cross_ok') is False else '—'}"
        )
    lines.append(f"持股：{row.get('shares')} 股　成本 {row.get('avg_price')}")
    if row.get("pnl_pct") is not None:
        lines.append(f"參考損益：{row.get('pnl_amount')}（{row.get('pnl_pct')}%）")
    lines.append(f"RSI：{row.get('rsi')}　量比：{row.get('volume_ratio')}　參考停損價：{row.get('stop_hint')}")
    lines.append(f"持有期間建議：{row.get('horizon')}")
    lines.append(f"建議說明：{row.get('suggestion', '')}")
    return "\n".join(lines)


def _full_report_advice_content(summary: str, items: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    tw = meta.get("advice_datetime_tw")
    header = "\n".join(
        [
            "========== Agent 操作建議 ==========",
            f"建議日期（UTC）：{meta.get('advice_date_utc', '—')}",
            f"建議時間（伺服器本地）：{meta.get('advice_date_local', '—')}",
            f"建議時間（台灣）：{tw or '—'}",
            f"報價擷取時間（UTC）：{meta.get('quote_fetched_at', '—')}",
            f"價格資料來源：{meta.get('price_data_provider', '—')}",
            "",
            "【摘要】",
            summary,
            "",
        ]
    )
    blocks = [header]
    for i, it in enumerate(items, 1):
        blocks.append(f"---------- 個股 {i} ----------")
        blocks.append(it.get("advice_content") or "")
    return "\n".join(blocks).strip()


def run_for_portfolio(stocks: list[dict]) -> dict[str, Any]:
    stocks = stocks or []
    now = datetime.now(timezone.utc)
    quote_fetched_at = now.isoformat(timespec="seconds")
    advice_date_utc = now.strftime("%Y-%m-%d")
    advice_date_local = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        from zoneinfo import ZoneInfo

        advice_datetime_tw = now.astimezone(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M 台灣")
    except Exception:
        advice_datetime_tw = None

    items = []
    for s in stocks:
        sym = str(s.get("symbol", "")).strip()
        if not sym:
            continue
        items.append(
            _analyze_one(
                sym,
                float(s.get("shares") or 0),
                float(s.get("avg_price") or 0),
                str(s.get("note") or ""),
                quote_fetched_at,
            )
        )

    up = sum(1 for x in items if (x.get("pnl_pct") or 0) > 0)
    down = sum(1 for x in items if (x.get("pnl_pct") or 0) < 0)
    summary = (
        f"共 {len(items)} 檔；參考獲利檔 {up}、虧損檔 {down}。"
        " 股價來自 Yahoo Finance（yfinance）公開行情，並於可行時以 Stooq 日線交叉比對；"
        "實際下單請以券商成交為準。非投資要約。"
    )
    if not items:
        summary = "尚無持股，請先新增或匯入持股後再執行分析。"

    meta = {
        "advice_date_utc": advice_date_utc,
        "advice_date_local": advice_date_local,
        "advice_datetime_tw": advice_datetime_tw,
        "quote_fetched_at": quote_fetched_at,
        "price_data_provider": f"{QUOTE_PROVIDER_PRIMARY}；交叉檢核：{QUOTE_PROVIDER_CROSS}（可取得時）",
    }
    advice_content = _full_report_advice_content(summary, items, meta)

    return {
        "agent": "holding_advisor_v2",
        "generated_at": quote_fetched_at,
        "advice_date": advice_date_utc,
        "advice_date_local": advice_date_local,
        "advice_datetime_tw": advice_datetime_tw,
        "advice_date_utc": advice_date_utc,
        "quote_fetched_at": quote_fetched_at,
        "price_data_provider": meta["price_data_provider"],
        "summary": summary,
        "advice_content": advice_content,
        "stocks": items,
    }
