"""
📸 SCREENSHOT AGENT
手機截圖持股辨識 Agent
使用 Claude Vision 從券商/股票 App 截圖中提取持股資訊
"""
import base64
import json
import logging
import re

import anthropic
import yfinance as yf

from config.settings import ANTHROPIC_AUTH_TOKEN, CLAUDE_MODEL
from stock_display_zh import resolve_stock_name_zh

logger = logging.getLogger(__name__)


def _has_cjk(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text))


class ScreenshotStock:
    """從截圖辨識出的單檔持股"""

    def __init__(self, symbol: str, name: str = "", shares: float = 0, avg_price: float = 0):
        self.symbol = symbol
        self.name = name
        self.shares = shares
        self.avg_price = avg_price

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "shares": self.shares,
            "avg_price": self.avg_price,
        }


class ScreenshotAgent:
    """截圖持股辨識 Agent"""

    SYSTEM_PROMPT = """你是專業的股票持倉截圖辨識 AI。
使用者會傳來手機截圖（台股或美股券商 App、股票 App 的持倉畫面），
你的任務是精確辨識其中的持股清單。

辨識規則（務必嚴格遵守）：
1. 台股上市：4～6 位數字代碼，輸出時加上「.TW」（例：2330 → 2330.TW；0050、00878 等 ETF 亦同）。
2. 台股上櫃：若畫面標示上櫃／櫃買或代碼屬櫃買常用檔，使用「.TWO」後綴（例：6488.TWO）。不確定則優先用 .TW。
3. 美股：1～5 個英文字母代碼（例：AAPL、NVDA）；勿把台股誤判為美股。
4. 股票名稱：逐字讀取畫面上的中文或英文全名／簡稱；ETF 須寫出完整名稱或截圖上的名稱（如「元大台灣50」）。
5. 股數：實際持有股數（台股為「股」；注意千分位逗號與「張」換算：1 張＝1000 股，若畫面為張請換算成股）。
6. 平均成本／均價：每股平均買入成本（勿把市值、參考損益、現價當成成本）。
7. 若某欄位在圖中完全看不到，該欄位填 0；名稱實在無法辨識可填 ""，但代碼務必正確。
8. 若同一檔重複列示，合併為一筆並加總股數（或取最合理的一筆並於 note 說明）。

回傳格式必須是合法的 JSON（不要包含任何說明文字），格式如下：
{
  "stocks": [
    {
      "symbol": "2330.TW",
      "name": "台積電",
      "shares": 100,
      "avg_price": 580.0
    }
  ],
  "confidence": 0.95,
  "note": "辨識備註（如：截圖模糊、部分資訊不清晰等）"
}

若圖片不是持倉截圖，或完全無法辨識，回傳：
{
  "stocks": [],
  "confidence": 0,
  "note": "無法辨識：請上傳持倉頁面截圖"
}"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_AUTH_TOKEN)

    def analyze(self, image_bytes: bytes, image_type: str = "image/jpeg") -> dict:
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        logger.info(f"[Screenshot] 開始辨識圖片 ({len(image_bytes)//1024} KB, {image_type})")

        try:
            message = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_type,
                                    "data": b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    "請仔細辨識這張截圖中的持倉資訊：代碼、中文／英文股票名稱、股數、平均成本。"
                                    "台股 ETF（如 0050）與一般股票皆須輸出正確後綴 .TW 或 .TWO。"
                                    "僅輸出 JSON，不要其他說明。"
                                ),
                            },
                        ],
                    }
                ],
            )

            raw = message.content[0].text.strip()
            logger.info(f"[Screenshot] Claude 回傳：{raw[:200]}...")

            result = self._parse_response(raw)
            result["stocks"] = self._enrich_names(result.get("stocks") or [])
            result["raw"] = raw
            return result

        except Exception as e:
            error_msg = str(e).lower()
            error_type = type(e).__name__
            
            # 檢查是否為 API token 或 rate limit 問題
            if "rate" in error_msg or "429" in error_msg or "quota" in error_msg:
                logger.error(
                    f"[Screenshot] Anthropic API 限制: {e} (錯誤類型: {error_type})\n"
                    f"請檢查：\n"
                    f"  1. ANTHROPIC_API_KEY 是否有效\n"
                    f"  2. API token 額度是否足夠\n"
                    f"  3. 是否請求過於頻繁"
                )
                note = f"Anthropic API 限制：{str(e)}\n請檢查 API token 額度或稍後再試。"
            else:
                logger.error(f"[Screenshot] 辨識失敗: {e} (錯誤類型: {error_type})")
                note = f"辨識失敗：{str(e)}"
            
            return {
                "stocks": [],
                "confidence": 0,
                "note": note,
                "raw": "",
            }

    def _parse_response(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
            stocks = self._normalize_stocks(data.get("stocks", []))
            return {
                "stocks": stocks,
                "confidence": float(data.get("confidence", 0)),
                "note": data.get("note", ""),
            }
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]+\}", raw)
        if match:
            try:
                data = json.loads(match.group())
                stocks = self._normalize_stocks(data.get("stocks", []))
                return {
                    "stocks": stocks,
                    "confidence": float(data.get("confidence", 0)),
                    "note": data.get("note", "無法完整解析"),
                }
            except Exception:
                pass

        logger.warning("[Screenshot] 無法解析 Claude 回傳的 JSON")
        return {"stocks": [], "confidence": 0, "note": "解析失敗"}

    def _enrich_names(self, stocks: list[dict]) -> list[dict]:
        """依代碼以公開資料補強／校正中文名稱（Vision 漏字或簡稱時）。"""
        out: list[dict] = []
        for s in stocks:
            if not isinstance(s, dict):
                continue
            sym = str(s.get("symbol", "")).strip().upper()
            if not sym:
                continue
            row = dict(s)
            nm = str(row.get("name", "")).strip()
            yf_info = None
            try:
                yf_info = yf.Ticker(sym).info or {}
            except Exception:
                yf_info = None
            resolved = resolve_stock_name_zh(sym, yf_info=yf_info, stored_name=nm)
            use = resolved
            if nm and len(nm) >= 2 and _has_cjk(nm) and nm not in (sym, resolved):
                use = nm
            elif not nm or len(nm) < 2 or nm.upper() == sym.replace(".TW", "").replace(".TWO", ""):
                use = resolved
            row["name"] = use
            out.append(row)
        return out

    def _normalize_stocks(self, raw_stocks: list) -> list[dict]:
        result = []
        for s in raw_stocks:
            if not isinstance(s, dict):
                continue

            symbol = str(s.get("symbol", "")).strip().upper()
            if not symbol:
                continue

            if re.match(r"^\d{4,6}$", symbol):
                symbol = f"{symbol}.TW"

            shares = self._parse_number(s.get("shares", 0))
            avg_price = self._parse_number(s.get("avg_price", 0))

            result.append({
                "symbol": symbol,
                "name": str(s.get("name", "")).strip(),
                "shares": shares,
                "avg_price": avg_price,
            })

        return result

    def _parse_number(self, value) -> float:
        try:
            if isinstance(value, (int, float)):
                return float(value)
            cleaned = re.sub(r"[,\s$NT$]", "", str(value))
            return float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return 0.0

    def format_preview(self, stocks: list[dict]) -> str:
        if not stocks:
            return "（未辨識到任何持股）"

        lines = []
        for i, s in enumerate(stocks, 1):
            symbol = s["symbol"]
            name = s.get("name", "")
            shares = s.get("shares", 0)
            avg_price = s.get("avg_price", 0)

            line = f"{i}. {symbol}"
            if name:
                line += f" ({name})"
            if shares > 0:
                line += f"　{shares:.0f} 股"
            if avg_price > 0:
                line += f"　均價 {avg_price:.1f}"
            lines.append(line)

        return "\n".join(lines)
