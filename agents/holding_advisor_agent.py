"""
Holding PWA — Agent 操作建議
股價以公開金融 API 取得並交叉確認：
  - 主來源：Yahoo Finance（yfinance，公開行情）
  - 輔助確認：Stooq 日線 CSV（無需 API Key，僅作價差檢核）

每筆報告含台股大盤約一個月展望、依大盤基調之個股短線建議、穩定獲利／短期持股分類之長期視角，
以及建議日期、各檔建議內文與整份 advice_content，供 advisor_store 持久化。
"""
from __future__ import annotations

import logging
import urllib.request
from datetime import datetime, timezone
from typing import Any

import yfinance as yf

from agents.tw_market_agent import run_one_month_tw_outlook
from stock_display_zh import resolve_stock_name_zh

logger = logging.getLogger(__name__)

QUOTE_PROVIDER_PRIMARY = "Yahoo Finance（yfinance 公開 API）"
QUOTE_PROVIDER_CROSS = "Stooq（日線 CSV 公開資料）"


def _holding_bucket(raw: str | None) -> str:
    v = (raw or "short_term").strip()
    return v if v in ("stable_profit", "short_term") else "short_term"


def _append_tw_market_hints(
    row: dict[str, Any],
    *,
    tw_bias: str,
    holding_bucket: str,
) -> None:
    """依台股大盤一個月基調與持股分類，補上短線方向與長期穩定獲利建議文案。"""
    sym = str(row.get("symbol", "")).strip().upper()
    is_tw = sym.endswith(".TW") or sym.endswith(".TWO")
    rsi = row.get("rsi")
    pnl = row.get("pnl_pct")
    bias = tw_bias if tw_bias in ("up", "down", "neutral") else "neutral"

    if not is_tw:
        row["short_term_direction_zh"] = "中性（非台股）"
        row["short_term_trade_hint_zh"] = (
            "台股大盤情境主要適用台股標的；美股請以美股大盤、個股基本面與技術面為主，勿過度依台股單一情境操作。"
        )
        if holding_bucket == "stable_profit":
            row["long_term_stable_advice_zh"] = (
                "長期配置請以產業前景、財務體質與股息政策為核心，並留意匯率對報酬的影響。"
            )
        else:
            row["long_term_stable_advice_zh"] = (
                "此檔為「短期持股」分類；若屬長期核心部位，建議改標「穩定獲利」以利對齊存股型檢視。"
            )
        return

    if bias == "up":
        row["short_term_direction_zh"] = "短線偏多"
        if rsi is not None and rsi >= 72:
            row["short_term_trade_hint_zh"] = (
                "大盤一個月基調偏多，但此檔 RSI 偏高，短線不宜追高；可續抱者請守停利或等待拉回再評估加碼。"
            )
        elif rsi is not None and rsi <= 38:
            row["short_term_trade_hint_zh"] = (
                "大盤偏多、個股相對弱勢或超跌，短線可觀察是否跌深反彈，若未站回關鍵價勿急於攤平。"
            )
        elif pnl is not None and pnl <= -10:
            row["short_term_trade_hint_zh"] = (
                "大盤偏多環境下此檔仍明顯虧損，短線若有反彈可視為調整部位結構的機會，並嚴守停損紀律。"
            )
        elif pnl is not None and pnl >= 20:
            row["short_term_trade_hint_zh"] = (
                "大盤偏多且個股獲利豐厚，短線可分批停利、鎖定獲利，保留核心部位順勢操作。"
            )
        else:
            row["short_term_trade_hint_zh"] = (
                "大盤基調偏多，短線可順勢操作並留意量能；跌破短均或停損價應執行紀律。"
            )
    elif bias == "down":
        row["short_term_direction_zh"] = "短線偏空"
        if rsi is not None and rsi <= 32:
            row["short_term_trade_hint_zh"] = (
                "大盤基調偏空且個股 RSI 偏低，短線防禦為先，反彈宜減碼或觀望，避免空手接刀。"
            )
        elif pnl is not None and pnl >= 15:
            row["short_term_trade_hint_zh"] = (
                "大盤偏空但個股仍有獲利，短線建議保守停利、降低曝險，保留現金等待落底訊號。"
            )
        else:
            row["short_term_trade_hint_zh"] = (
                "大盤基調偏空，短線以控管風險為主，避免重壓單一產業，停損與總曝險宜從嚴。"
            )
    else:
        row["short_term_direction_zh"] = "短線中性"
        row["short_term_trade_hint_zh"] = (
            "大盤一個月展望中性整理，個股短線宜區間操作或觀望突破／跌破後再跟進。"
        )

    if holding_bucket == "stable_profit":
        if bias == "up":
            row["long_term_stable_advice_zh"] = (
                "此檔列為「穩定獲利」：長期以配息與競爭力為軸，大盤偏多時可續抱核心、僅在估值明顯過熱或基本面轉弱時減碼。"
            )
        elif bias == "down":
            row["long_term_stable_advice_zh"] = (
                "此檔列為「穩定獲利」：長期仍看公司現金流與產業地位；大盤偏空時可檢視是否趁低加碼核心標的，"
                "但須分散產業並避免單一槓桿過大。"
            )
        else:
            row["long_term_stable_advice_zh"] = (
                "此檔列為「穩定獲利」：長線建議定期定額或再平衡，不因短線中性整理頻繁進出，聚焦體質與股息再投資。"
            )
    else:
        row["long_term_stable_advice_zh"] = (
            "此檔為「短期持股」：長期存股型建議請改標「穩定獲利」；目前以波段與停損停利紀律為主。"
        )


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
    stored_name: str = "",
    holding_bucket: str = "short_term",
    tw_bias: str = "neutral",
) -> dict[str, Any]:
    bucket = _holding_bucket(holding_bucket)
    row: dict[str, Any] = {
        "symbol": symbol,
        "holding_bucket": bucket,
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
        row["name"] = resolve_stock_name_zh(symbol, yf_info=info, stored_name=stored_name)

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
            _append_tw_market_hints(row, tw_bias=tw_bias, holding_bucket=bucket)
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

    _append_tw_market_hints(row, tw_bias=tw_bias, holding_bucket=bucket)
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
    lines.append(f"持股分類：{'穩定獲利' if row.get('holding_bucket') == 'stable_profit' else '短期持股'}")
    lines.append(f"短線方向（對齊台股大盤一個月基調）：{row.get('short_term_direction_zh', '—')}")
    lines.append(f"短線操作參考：{row.get('short_term_trade_hint_zh', '—')}")
    lines.append(f"長期穩定獲利／存股視角：{row.get('long_term_stable_advice_zh', '—')}")
    lines.append(f"建議說明：{row.get('suggestion', '')}")
    return "\n".join(lines)


def _full_report_advice_content(
    summary: str,
    items: list[dict[str, Any]],
    meta: dict[str, Any],
    tw_outlook: dict[str, Any] | None,
) -> str:
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
        ]
    )
    tw_block = ""
    if tw_outlook:
        lbl = tw_outlook.get("bias_label_zh") or "—"
        summ = tw_outlook.get("one_month_summary_zh") or ""
        conf = tw_outlook.get("confidence_0_to_1")
        conf_s = f"{float(conf):.2f}" if conf is not None else "—"
        pts = tw_outlook.get("key_watchpoints_zh") or []
        pt_lines = "\n".join(f"  · {p}" for p in pts) if isinstance(pts, list) else str(pts)
        tw_block = (
            "\n【台股大盤 · 約一個月展望（Agent 推估）】\n"
            f"基調：{lbl}（bias={tw_outlook.get('bias_one_month', '—')}）　信心度：{conf_s}\n"
            f"{summ}\n"
            f"觀察重點：\n{pt_lines}\n"
            "（以上為情境推估，非投資要約；實際下單請以自身風險承受度為準。）\n"
        )
    blocks = [
        header + tw_block + "【摘要】\n" + summary + "\n",
    ]
    for i, it in enumerate(items, 1):
        blocks.append(f"---------- 個股 {i} ----------")
        blocks.append(it.get("advice_content") or "")
    return "\n".join(blocks).strip()


def run_for_portfolio(stocks: list[dict]) -> dict[str, Any]:
    stocks = stocks or []
    tw_outlook = run_one_month_tw_outlook()
    tw_bias = str(tw_outlook.get("bias_one_month") or "neutral").lower()
    if tw_bias not in ("up", "down", "neutral"):
        tw_bias = "neutral"

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
                str(s.get("name") or ""),
                str(s.get("holding_bucket") or "short_term"),
                tw_bias,
            )
        )

    up = sum(1 for x in items if (x.get("pnl_pct") or 0) > 0)
    down = sum(1 for x in items if (x.get("pnl_pct") or 0) < 0)
    bias_zh = tw_outlook.get("bias_label_zh") or tw_bias
    summary = (
        f"共 {len(items)} 檔；參考獲利檔 {up}、虧損檔 {down}。"
        f" 台股大盤約一個月基調（Agent）：{bias_zh}。"
        " 股價來自 Yahoo Finance（yfinance）公開行情，並於可行時以 Stooq 日線交叉比對；"
        "實際下單請以券商成交為準。非投資要約。"
    )
    if not items:
        summary = "尚無持股，請先新增或匯入持股後再執行分析。"

    tw_report = dict(tw_outlook)
    tw_report.pop("raw_model", None)

    meta = {
        "advice_date_utc": advice_date_utc,
        "advice_date_local": advice_date_local,
        "advice_datetime_tw": advice_datetime_tw,
        "quote_fetched_at": quote_fetched_at,
        "price_data_provider": f"{QUOTE_PROVIDER_PRIMARY}；交叉檢核：{QUOTE_PROVIDER_CROSS}（可取得時）",
    }
    advice_content = _full_report_advice_content(summary, items, meta, tw_report)

    return {
        "agent": "holding_advisor_v3",
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
        "tw_market_outlook": tw_report,
    }
