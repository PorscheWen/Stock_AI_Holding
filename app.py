"""
Stock_AI_Holding — Flask：PWA 持股、截圖辨識 API、健康檢查
"""
import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
import yfinance as yf

from agents.screenshot_agent import ScreenshotAgent
from database.portfolio_db import PortfolioDB

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
    return jsonify({
        "service": "Stock_AI_Holding",
        "pwa": "/app",
        "health": "/health",
    }), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok", "mode": "holding_pwa"}), 200


@app.get("/app")
def pwa_page():
    return render_template("pwa.html")


@app.get("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js", mimetype="application/javascript")


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
    ok = db.add_stock(
        uid,
        symbol,
        float(data.get("shares", 0)),
        float(data.get("avg_price", 0)),
        str(data.get("note", "")),
    )
    return jsonify({"success": ok, "symbol": symbol})


@app.delete("/api/portfolio/<symbol>")
def api_portfolio_remove(symbol: str):
    uid, err = _require_user_id()
    if err:
        return err
    ok = db.remove_stock(uid, symbol.upper())
    return jsonify({"success": ok})


@app.delete("/api/portfolio")
def api_portfolio_clear():
    uid, err = _require_user_id()
    if err:
        return err
    db.clear_portfolio(uid)
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
        try:
            info = yf.Ticker(symbol).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            prev = info.get("previousClose") or 0
            change = round(price - prev, 2) if price and prev else 0
            pct = round(change / prev * 100, 2) if prev else 0
            entry.update({
                "current_price": round(float(price), 2),
                "change": change,
                "change_pct": pct,
                "name": info.get("shortName") or info.get("longName", symbol),
            })
        except Exception:
            entry.update({"current_price": 0, "change": 0, "change_pct": 0, "name": symbol})
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
    return jsonify(db.batch_add_stocks(uid, stocks))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("Stock_AI_Holding：PWA /app、持股 API、截圖辨識")
    app.run(host="0.0.0.0", port=port, debug=False)
