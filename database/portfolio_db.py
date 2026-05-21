"""
持股資料庫管理
使用 JSON 檔案儲存使用者持股資訊
"""
import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

# 持股分類：穩定獲利（長期核心）／短期持股（波段或交易）
HOLDING_BUCKETS = frozenset({"stable_profit", "short_term"})
LONG_TERM_BUCKET_ALIASES = frozenset({
    "stable_profit",
    "long_term",
    "long",
    "stable",
    "長期",
    "長線",
    "穩定獲利",
    "穩定",
})
SHORT_TERM_BUCKET_ALIASES = frozenset({
    "short_term",
    "short",
    "trade",
    "短期",
    "短線",
    "波段",
    "交易",
})


def _normalize_bucket(raw: str | None) -> str:
    raw_v = (raw or "").strip()
    if not raw_v:
        return "short_term"

    v = raw_v.lower().replace("-", "_").replace(" ", "_")
    if v in HOLDING_BUCKETS:
        return v
    if v in LONG_TERM_BUCKET_ALIASES or raw_v in LONG_TERM_BUCKET_ALIASES:
        return "stable_profit"
    if v in SHORT_TERM_BUCKET_ALIASES or raw_v in SHORT_TERM_BUCKET_ALIASES:
        return "short_term"
    return "short_term"


def _normalize_stock_row(stock: dict) -> dict:
    d = dict(stock)
    d["holding_bucket"] = _normalize_bucket(d.get("holding_bucket"))
    return d

# 資料庫檔案路徑
DB_DIR = Path("database/data")
DB_FILE = DB_DIR / "portfolios.json"


class PortfolioDB:
    """持股資料庫管理類別"""
    
    def __init__(self):
        self._ensure_db()
    
    def _ensure_db(self):
        """確保資料庫目錄和檔案存在"""
        DB_DIR.mkdir(parents=True, exist_ok=True)
        if not DB_FILE.exists():
            DB_FILE.write_text("{}")
            logger.info(f"初始化資料庫: {DB_FILE}")
    
    def _load(self) -> dict:
        """載入資料庫"""
        try:
            return json.loads(DB_FILE.read_text())
        except Exception as e:
            logger.error(f"載入資料庫失敗: {e}")
            return {}
    
    def _save(self, data: dict):
        """儲存資料庫"""
        try:
            DB_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"儲存資料庫失敗: {e}")
    
    # ── 使用者持股管理 ───────────────────────────────────
    def add_stock(self, user_id: str, symbol: str, shares: float = 0,
                  avg_price: float = 0, note: str = "", name: str = "",
                  holding_bucket: str = "short_term") -> bool:
        """
        新增持股
        
        Args:
            user_id: LINE 使用者 ID
            symbol: 股票代碼 (例如: "2330.TW", "AAPL")
            shares: 持股數量
            avg_price: 平均成本
            note: 備註
            name: 股票名稱 (選填)
            holding_bucket: stable_profit（穩定獲利）或 short_term（短期持股）

        Returns:
            成功回傳 True
        """
        data = self._load()
        
        if user_id not in data:
            data[user_id] = {
                "created_at": datetime.now().isoformat(),
                "stocks": {}
            }
        
        bucket = _normalize_bucket(holding_bucket)

        data[user_id]["stocks"][symbol] = {
            "symbol": symbol,
            "name": name,
            "shares": shares,
            "avg_price": avg_price,
            "note": note,
            "holding_bucket": bucket,
            "added_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        self._save(data)
        logger.info(f"新增持股: user={user_id}, symbol={symbol}, name={name}, bucket={bucket}, shares={shares}")
        return True
    
    def remove_stock(self, user_id: str, symbol: str) -> bool:
        """
        移除持股
        
        Args:
            user_id: LINE 使用者 ID
            symbol: 股票代碼
        
        Returns:
            成功回傳 True，失敗回傳 False
        """
        data = self._load()
        
        if user_id not in data or symbol not in data[user_id]["stocks"]:
            logger.warning(f"持股不存在: user={user_id}, symbol={symbol}")
            return False
        
        del data[user_id]["stocks"][symbol]
        self._save(data)
        logger.info(f"移除持股: user={user_id}, symbol={symbol}")
        return True
    
    def get_portfolio(self, user_id: str) -> list[dict]:
        """
        取得使用者所有持股
        
        Args:
            user_id: LINE 使用者 ID
        
        Returns:
            持股清單 [{"symbol": "2330.TW", "shares": 100, ...}, ...]
        """
        data = self._load()
        
        if user_id not in data:
            return []
        
        stocks = data[user_id]["stocks"]
        return [_normalize_stock_row(v) for v in stocks.values()]
    
    def get_stock(self, user_id: str, symbol: str) -> Optional[dict]:
        """
        取得特定持股資訊
        
        Args:
            user_id: LINE 使用者 ID
            symbol: 股票代碼
        
        Returns:
            持股資訊或 None
        """
        data = self._load()
        
        if user_id not in data or symbol not in data[user_id]["stocks"]:
            return None
        
        return _normalize_stock_row(data[user_id]["stocks"][symbol])
    
    def get_all_symbols(self, user_id: str) -> list[str]:
        """
        取得使用者所有持股代碼列表
        
        Args:
            user_id: LINE 使用者 ID
        
        Returns:
            股票代碼列表 ["2330.TW", "AAPL", ...]
        """
        portfolio = self.get_portfolio(user_id)
        return [stock["symbol"] for stock in portfolio]
    
    def clear_portfolio(self, user_id: str) -> bool:
        """
        清空使用者所有持股
        
        Args:
            user_id: LINE 使用者 ID
        
        Returns:
            成功回傳 True
        """
        data = self._load()
        
        if user_id in data:
            data[user_id]["stocks"] = {}
            self._save(data)
            logger.info(f"清空持股: user={user_id}")
        
        return True
    
    def _rename_stock(self, user_id: str, old_symbol: str, new_symbol: str, **kwargs) -> bool:
        """變更股票代碼（key），並套用其餘欄位更新。"""
        data = self._load()
        if user_id not in data or old_symbol not in data[user_id]["stocks"]:
            return False
        new_symbol = new_symbol.strip().upper()
        if not new_symbol:
            return False
        if new_symbol != old_symbol and new_symbol in data[user_id]["stocks"]:
            logger.warning("代碼已存在: %s", new_symbol)
            return False
        stock = data[user_id]["stocks"].pop(old_symbol)
        stock["symbol"] = new_symbol
        for key, value in kwargs.items():
            if key == "symbol":
                continue
            if key == "holding_bucket":
                stock[key] = _normalize_bucket(str(value))
            elif key == "price_override":
                if value is None or value == "":
                    stock.pop("price_override", None)
                else:
                    stock["price_override"] = float(value)
            elif key in ("shares", "avg_price", "note", "name"):
                stock[key] = value
        stock["updated_at"] = datetime.now().isoformat()
        data[user_id]["stocks"][new_symbol] = stock
        self._save(data)
        logger.info("更名持股: user=%s, %s -> %s", user_id, old_symbol, new_symbol)
        return True

    def update_stock(self, user_id: str, symbol: str, **kwargs) -> bool:
        """
        更新持股資訊
        
        Args:
            user_id: LINE 使用者 ID
            symbol: 股票代碼
            **kwargs: shares, avg_price, note, name, holding_bucket, price_override, symbol（新代碼）
        
        Returns:
            成功回傳 True，失敗回傳 False
        """
        new_symbol = kwargs.get("symbol")
        if new_symbol is not None:
            new_symbol = str(new_symbol).strip().upper()
            if new_symbol and new_symbol != symbol:
                rest = {k: v for k, v in kwargs.items() if k != "symbol"}
                return self._rename_stock(user_id, symbol, new_symbol, **rest)

        data = self._load()
        
        if user_id not in data or symbol not in data[user_id]["stocks"]:
            logger.warning(f"持股不存在: user={user_id}, symbol={symbol}")
            return False
        
        stock = data[user_id]["stocks"][symbol]
        
        for key, value in kwargs.items():
            if key == "symbol":
                continue
            if key == "holding_bucket":
                stock[key] = _normalize_bucket(str(value))
            elif key == "price_override":
                if value is None or value == "":
                    stock.pop("price_override", None)
                else:
                    stock["price_override"] = float(value)
            elif key in ["shares", "avg_price", "note", "name"]:
                stock[key] = value
        
        stock["updated_at"] = datetime.now().isoformat()
        
        self._save(data)
        logger.info(f"更新持股: user={user_id}, symbol={symbol}, updates={kwargs}")
        return True
    
    # ── 匯入/匯出功能 ───────────────────────────────────
    def import_from_csv(self, user_id: str, csv_file: str, 
                       clear_existing: bool = False) -> dict:
        """
        從 CSV 檔案匯入持股
        
        CSV 格式：symbol,shares,avg_price,note,name,holding_bucket
        範例：
        2330.TW,100,580,台積電,台積電,stable_profit
        AAPL,50,185,蘋果,Apple,short_term
        
        Args:
            user_id: LINE 使用者 ID
            csv_file: CSV 檔案路徑
            clear_existing: 是否清空現有持股
        
        Returns:
            {"success": int, "failed": int, "errors": List[str]}
        """
        result = {"success": 0, "failed": 0, "errors": []}
        
        try:
            csv_path = Path(csv_file)
            if not csv_path.exists():
                result["errors"].append(f"檔案不存在: {csv_file}")
                return result
            
            # 清空現有持股（如果需要）
            if clear_existing:
                self.clear_portfolio(user_id)
            
            # 讀取 CSV
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        symbol = row.get('symbol', '').strip().upper()
                        name = row.get('name', '').strip()
                        shares = float(row.get('shares', 0))
                        avg_price = float(row.get('avg_price', 0))
                        note = row.get('note', '').strip()
                        bucket = _normalize_bucket(row.get('holding_bucket'))
                        
                        if not symbol:
                            result["failed"] += 1
                            result["errors"].append(f"跳過空的股票代碼")
                            continue
                        
                        if self.add_stock(user_id, symbol, shares, avg_price, note, name, bucket):
                            result["success"] += 1
                        else:
                            result["failed"] += 1
                            result["errors"].append(f"新增失敗: {symbol}")
                            
                    except Exception as e:
                        result["failed"] += 1
                        result["errors"].append(f"處理資料失敗: {str(e)}")
            
            logger.info(f"CSV 匯入完成: user={user_id}, success={result['success']}, failed={result['failed']}")
            return result
            
        except Exception as e:
            result["errors"].append(f"讀取 CSV 失敗: {str(e)}")
            logger.error(f"CSV 匯入失敗: {e}")
            return result
    
    def import_from_json(self, user_id: str, json_file: str,
                        clear_existing: bool = False) -> dict:
        """
        從 JSON 檔案匯入持股
        
        JSON 格式：
        [
            {"symbol": "2330.TW", "shares": 100, "avg_price": 580, "note": "台積電", "name": "台積電", "holding_bucket": "stable_profit"},
            {"symbol": "AAPL", "shares": 50, "avg_price": 185, "note": "蘋果", "name": "Apple", "holding_bucket": "short_term"}
        ]
        
        Args:
            user_id: LINE 使用者 ID
            json_file: JSON 檔案路徑
            clear_existing: 是否清空現有持股
        
        Returns:
            {"success": int, "failed": int, "errors": List[str]}
        """
        result = {"success": 0, "failed": 0, "errors": []}
        
        try:
            json_path = Path(json_file)
            if not json_path.exists():
                result["errors"].append(f"檔案不存在: {json_file}")
                return result
            
            # 清空現有持股（如果需要）
            if clear_existing:
                self.clear_portfolio(user_id)
            
            # 讀取 JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                stocks = json.load(f)
            
            if not isinstance(stocks, list):
                result["errors"].append("JSON 格式錯誤，應為陣列格式")
                return result
            
            for stock in stocks:
                try:
                    symbol = stock.get('symbol', '').strip().upper()
                    name = stock.get('name', '').strip()
                    shares = float(stock.get('shares', 0))
                    avg_price = float(stock.get('avg_price', 0))
                    note = stock.get('note', '').strip()
                    bucket = _normalize_bucket(stock.get('holding_bucket'))
                    
                    if not symbol:
                        result["failed"] += 1
                        result["errors"].append(f"跳過空的股票代碼")
                        continue
                    
                    if self.add_stock(user_id, symbol, shares, avg_price, note, name, bucket):
                        result["success"] += 1
                    else:
                        result["failed"] += 1
                        result["errors"].append(f"新增失敗: {symbol}")
                        
                except Exception as e:
                    result["failed"] += 1
                    result["errors"].append(f"處理資料失敗: {str(e)}")
            
            logger.info(f"JSON 匯入完成: user={user_id}, success={result['success']}, failed={result['failed']}")
            return result
            
        except Exception as e:
            result["errors"].append(f"讀取 JSON 失敗: {str(e)}")
            logger.error(f"JSON 匯入失敗: {e}")
            return result
    
    def export_to_csv(self, user_id: str, csv_file: str) -> bool:
        """
        匯出持股到 CSV 檔案
        
        Args:
            user_id: LINE 使用者 ID
            csv_file: CSV 檔案路徑
        
        Returns:
            成功回傳 True
        """
        try:
            portfolio = self.get_portfolio(user_id)
            
            csv_path = Path(csv_file)
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['symbol', 'shares', 'avg_price', 'note']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                for stock in portfolio:
                    writer.writerow({
                        'symbol': stock['symbol'],
                        'shares': stock.get('shares', 0),
                        'avg_price': stock.get('avg_price', 0),
                        'note': stock.get('note', ''),
                    })
            
            logger.info(f"CSV 匯出完成: user={user_id}, file={csv_file}, stocks={len(portfolio)}")
            return True
            
        except Exception as e:
            logger.error(f"CSV 匯出失敗: {e}")
            return False
    
    def export_to_json(self, user_id: str, json_file: str) -> bool:
        """
        匯出持股到 JSON 檔案
        
        Args:
            user_id: LINE 使用者 ID
            json_file: JSON 檔案路徑
        
        Returns:
            成功回傳 True
        """
        try:
            portfolio = self.get_portfolio(user_id)
            
            json_path = Path(json_file)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 只匯出必要欄位
            export_data = []
            for stock in portfolio:
                export_data.append({
                    'symbol': stock['symbol'],
                    'shares': stock.get('shares', 0),
                    'avg_price': stock.get('avg_price', 0),
                    'note': stock.get('note', ''),
                })
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"JSON 匯出完成: user={user_id}, file={json_file}, stocks={len(portfolio)}")
            return True
            
        except Exception as e:
            logger.error(f"JSON 匯出失敗: {e}")
            return False
    
    def batch_add_stocks(self, user_id: str, stocks: List[dict]) -> dict:
        """
        批量新增持股
        
        Args:
            user_id: LINE 使用者 ID
            stocks: 持股列表 [{"symbol": "2330.TW", "name": "台積電", "shares": 100, ...}, ...]
        
        Returns:
            {"success": int, "failed": int, "errors": List[str]}
        """
        result = {"success": 0, "failed": 0, "errors": []}
        
        for stock in stocks:
            try:
                symbol = stock.get('symbol', '').strip().upper()
                name = stock.get('name', '').strip()
                shares = float(stock.get('shares', 0))
                avg_price = float(stock.get('avg_price', 0))
                note = stock.get('note', '').strip()
                bucket = _normalize_bucket(stock.get("holding_bucket"))

                if not symbol:
                    result["failed"] += 1
                    result["errors"].append(f"跳過空的股票代碼")
                    continue
                
                if self.add_stock(user_id, symbol, shares, avg_price, note, name, bucket):
                    result["success"] += 1
                else:
                    result["failed"] += 1
                    result["errors"].append(f"新增失敗: {symbol}")
                    
            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"處理資料失敗: {str(e)}")
        
        return result
