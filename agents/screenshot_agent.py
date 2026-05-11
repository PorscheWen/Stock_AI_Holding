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

from config.settings import ANTHROPIC_AUTH_TOKEN, CLAUDE_MODEL

logger = logging.getLogger(__name__)


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

辨識規則：
1. 台股代碼格式：4位數字，需在後面加上「.TW」（例：2330 → 2330.TW）
2. 美股代碼格式：1-5個英文字母（例：AAPL、NVDA）
3. 股數：持有的股票數量（台股單位為「股」，美股單位為 shares）
4. 平均成本/均價：每股的平均買入成本（非市值、非損益）
5. 若圖片中找不到某欄位，返回 0

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
                max_tokens=2048,
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
                                "text": "請辨識這張截圖中的持倉資訊，以 JSON 格式回傳。",
                            },
                        ],
                    }
                ],
            )

            raw = message.content[0].text.strip()
            logger.info(f"[Screenshot] Claude 回傳：{raw[:200]}...")

            result = self._parse_response(raw)
            result["raw"] = raw
            return result

        except Exception as e:
            logger.error(f"[Screenshot] 辨識失敗: {e}")
            return {
                "stocks": [],
                "confidence": 0,
                "note": f"辨識失敗：{str(e)}",
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
