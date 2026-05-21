"""
Stock_AI_Holding — Flask：PWA 持股、截圖辨識 API、健康檢查
"""
import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, redirect, render_template, request, send_from_directory
import yfinance as yf

from agents.screenshot_agent import ScreenshotAgent
from agents.holding_advisor_agent import run_for_portfolio
from database.portfolio_db import PortfolioDB
from database import advisor_store
from stock_display_zh import resolve_stock_name_zh
from utils import notification

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
db = PortfolioDB()


def _require_user_id() -> tuple[str | None, tuple | None]:
    uid = request.headers.get("X-User-ID", "").strip()
    if not uid:
        return None, (jsonify({"error": "X-User-ID header required"}), 400)
    return uid, None


@app.get("/")
def index():
    return redirect("/app")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "mode": "holding_pwa"}), 200


@app.get("/app")
def pwa_page():
    resp = make_response(render_template("pwa.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.get("/sw.js")
def service_worker():
    resp = send_from_directory("static", "sw.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.get("/api/portfolio")
def api_portfolio_get():
    uid, err = _require_user_id()
    if err:
        return err
    return jsonify({"stocks": db.get_portfolio(uid)})


@app.post("/api/portfolio")
def api_portfolio_add():
    uid, err = _require_user_id()
    if err:
        return err
    data = request.get_json(force=True) or {}
    symbol = str(data.get("symbol", "")).strip().upper()
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    
    shares = float(data.get("shares", 0))
    avg_price = float(data.get("avg_price", 0))
    name = str(data.get("name", ""))
    
    ok = db.add_stock(
        uid,
        symbol,
        shares,
        avg_price,
        str(data.get("note", "")),
        name,
        str(data.get("holding_bucket", "short_term")),
    )
    
    # 发送通知
    if ok:
        total_stocks = len(db.get_portfolio(uid))
        notification.notify_stock_added(uid, symbol, name, shares, avg_price, total_stocks)
    
    return jsonify({"success": ok, "symbol": symbol})


@app.patch("/api/portfolio/<symbol>")
def api_portfolio_patch(symbol: str):
    """更新單筆持股（股數、均價、備註、名稱、分類）。"""
    uid, err = _require_user_id()
    if err:
        return err
    sym = symbol.strip().upper()
    data = request.get_json(force=True) or {}
    updates: dict = {}
    if "shares" in data:
        try:
            updates["shares"] = float(data["shares"])
        except (TypeError, ValueError):
            return jsonify({"error": "invalid shares"}), 400
    if "avg_price" in data:
        try:
            updates["avg_price"] = float(data["avg_price"])
        except (TypeError, ValueError):
            return jsonify({"error": "invalid avg_price"}), 400
    if "note" in data:
        updates["note"] = str(data.get("note") or "")
    if "name" in data:
        updates["name"] = str(data.get("name") or "")
    if "holding_bucket" in data:
        updates["holding_bucket"] = str(data.get("holding_bucket") or "short_term")
    if not updates:
        return jsonify({"error": "no updatable fields"}), 400
    ok = db.update_stock(uid, sym, **updates)
    
    # 发送通知
    if ok:
        stock_name = updates.get("name", sym)
        total_stocks = len(db.get_portfolio(uid))
        notification.notify_stock_updated(uid, sym, stock_name, updates, total_stocks)
    
    return jsonify({"success": ok, "symbol": sym})


@app.delete("/api/portfolio/<symbol>")
def api_portfolio_remove(symbol: str):
    uid, err = _require_user_id()
    if err:
        return err
    sym = symbol.upper()
    ok = db.remove_stock(uid, sym)
    
    # 发送通知
    if ok:
        total_stocks = len(db.get_portfolio(uid))
        notification.notify_stock_deleted(uid, sym, total_stocks)
    
    return jsonify({"success": ok})


@app.delete("/api/portfolio")
def api_portfolio_clear():
    uid, err = _require_user_id()
    if err:
        return err
    db.clear_portfolio(uid)
    
    # 发送通知
    notification.notify_portfolio_cleared(uid)
    
    return jsonify({"success": True})


@app.get("/api/portfolio/prices")
def api_portfolio_prices():
    uid, err = _require_user_id()
    if err:
        return err
    stocks = db.get_portfolio(uid)
    results = []
    for stock in stocks:
        symbol = stock["symbol"]
        entry = dict(stock)
        stored_nm = str(stock.get("name") or "")
        try:
            info = yf.Ticker(symbol).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            prev = info.get("previousClose") or 0
            change = round(price - prev, 2) if price and prev else 0
            pct = round(change / prev * 100, 2) if prev else 0
            
            # 計算損益率
            avg_price = float(stock.get("avg_price") or 0)
            pnl_amount = None
            pnl_pct = None
            if price and avg_price:
                shares = float(stock.get("shares") or 0)
                pnl_amount = round((price - avg_price) * shares, 2)
                pnl_pct = round((price - avg_price) / avg_price * 100, 2)
            
            entry.update({
                "current_price": round(float(price), 2),
                "change": change,
                "change_pct": pct,
                "pnl_amount": pnl_amount,
                "pnl_pct": pnl_pct,
                "name": resolve_stock_name_zh(symbol, yf_info=info or {}, stored_name=stored_nm),
            })
        except Exception:
            entry.update({
                "current_price": 0,
                "change": 0,
                "change_pct": 0,
                "pnl_amount": None,
                "pnl_pct": None,
                "name": resolve_stock_name_zh(symbol, yf_info=None, stored_name=stored_nm),
            })
        results.append(entry)
    return jsonify({"stocks": results})


@app.post("/api/screenshot")
def api_screenshot():
    uid, err = _require_user_id()
    if err:
        return err
    if "image" not in request.files:
        return jsonify({"error": "image file required"}), 400
    img_file = request.files["image"]
    img_bytes = img_file.read()
    content_type = img_file.content_type or "image/jpeg"
    result = ScreenshotAgent().analyze(img_bytes, image_type=content_type)
    return jsonify(result)


@app.post("/api/screenshot/import")
def api_screenshot_import():
    uid, err = _require_user_id()
    if err:
        return err
    data = request.get_json(force=True) or {}
    stocks = data.get("stocks", [])
    if not stocks:
        return jsonify({"error": "stocks required"}), 400
    
    result = db.batch_add_stocks(uid, stocks)
    
    # 发送通知
    if result.get("success", 0) > 0:
        total_stocks = len(db.get_portfolio(uid))
        notification.notify_screenshot_imported(
            uid, 
            result.get("success", 0), 
            result.get("failed", 0), 
            total_stocks
        )
    
    return jsonify(result)


@app.post("/api/advisor/run")
def api_advisor_run():
    """一鍵執行 Agent 建議：依目前持股分析並寫入歷史。"""
    uid, err = _require_user_id()
    if err:
        return err
    stocks = db.get_portfolio(uid)
    eligible = []
    skipped_symbols: list[str] = []
    for s in stocks:
        try:
            shares = float(s.get("shares") or 0)
        except (TypeError, ValueError):
            shares = 0.0
        if shares <= 1:
            skipped_symbols.append(str(s.get("symbol") or ""))
            continue
        eligible.append(s)

    report = run_for_portfolio(eligible)
    report["analysis_filter"] = {
        "rule": "shares > 1",
        "input_count": len(stocks),
        "analyzed_count": len(eligible),
        "skipped_count": len(skipped_symbols),
        "skipped_symbols": [x for x in skipped_symbols if x],
    }
    saved = advisor_store.append_report(uid, report)
    return jsonify({"ok": True, "report": saved}), 200


@app.get("/api/advisor/latest")
def api_advisor_latest():
    """最近一次儲存的建議報告。"""
    uid, err = _require_user_id()
    if err:
        return err
    rep = advisor_store.get_latest(uid)
    if not rep:
        return jsonify({"report": None}), 200
    return jsonify({"report": rep}), 200


@app.get("/api/advisor/history")
def api_advisor_history():
    """歷史建議列表（精簡，預設最近 10 筆）。"""
    uid, err = _require_user_id()
    if err:
        return err
    try:
        limit = int(request.args.get("limit", "10"))
    except ValueError:
        limit = 10
    reps = advisor_store.get_history(uid, limit=limit)
    slim = [
        {
            "id": r.get("id"),
            "generated_at": r.get("generated_at"),
            "advice_date": r.get("advice_date"),
            "advice_datetime_tw": r.get("advice_datetime_tw"),
            "quote_fetched_at": r.get("quote_fetched_at"),
            "summary": r.get("summary"),
            "stock_count": len(r.get("stocks") or []),
            "has_full_text": bool(r.get("advice_content")),
        }
        for r in reps
    ]
    return jsonify({"items": slim}), 200


@app.get("/api/portfolio/export")
def api_portfolio_export():
    """匯出持股為 JSON 格式。"""
    uid, err = _require_user_id()
    if err:
        return err
    stocks = db.get_portfolio(uid)
    export_data = [
        {
            "symbol": stock["symbol"],
            "name": stock.get("name", ""),
            "shares": stock.get("shares", 0),
            "avg_price": stock.get("avg_price", 0),
            "holding_bucket": stock.get("holding_bucket", "short_term"),
            "note": stock.get("note", ""),
        }
        for stock in stocks
    ]
    return jsonify({"stocks": export_data, "count": len(export_data)}), 200


@app.post("/api/portfolio/import")
def api_portfolio_import():
    """匯入持股資料（JSON 格式），可選擇是否清空現有持股。"""
    uid, err = _require_user_id()
    if err:
        return err
    data = request.get_json(force=True) or {}
    stocks = data.get("stocks", [])
    clear_existing = data.get("clear_existing", False)
    
    if not stocks or not isinstance(stocks, list):
        return jsonify({"error": "stocks array required"}), 400
    
    # 如果需要清空現有持股
    if clear_existing:
        db.clear_portfolio(uid)
    
    # 批量匯入
    result = db.batch_add_stocks(uid, stocks)
    
    # 发送通知
    if result.get("success", 0) > 0:
        total_stocks = len(db.get_portfolio(uid))
        notification.notify_portfolio_imported(
            uid, 
            result.get("success", 0), 
            result.get("failed", 0), 
            total_stocks
        )
    
    return jsonify(result), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Stock_AI_Holding：PWA /app、持股 API、截圖辨識")
    app.run(host="0.0.0.0", port=port, debug=False)
