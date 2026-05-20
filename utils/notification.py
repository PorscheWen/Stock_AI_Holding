"""
持股更新通知模块 - LINE Push Message
"""
import logging
import os
from datetime import datetime
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or os.getenv("CHANNEL_ACCESS_TOKEN", "")
APP_URL = (os.getenv("APP_URL", "") or "").strip().rstrip("/")
LINE_API = "https://api.line.me/v2/bot/message/push"


def send_portfolio_update_notification(
    user_id: str,
    action: str,
    details: str,
    stock_count: int = 0
) -> bool:
    """
    发送持股更新通知到 LINE
    
    Args:
        user_id: LINE User ID
        action: 操作类型 (新增/更新/删除/匯入/匯出)
        details: 详细内容
        stock_count: 持股总数
    
    Returns:
        是否发送成功
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.warning("未设定 LINE_CHANNEL_ACCESS_TOKEN，跳过推送通知")
        return False
    
    if not user_id or user_id.startswith("pwa_"):
        logger.info(f"User ID {user_id} 为本地 ID，跳过推送通知")
        return False
    
    # 构建网页链接
    app_base = APP_URL if APP_URL else "https://your-app.com/app"
    if not app_base.endswith("/app"):
        app_base = app_base.rstrip("/") + "/app"
    
    # 获取当前时间
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建推送消息
    message_text = f"""📊 持股更新通知

操作：{action}
時間：{now}
{details}
目前持股總數：{stock_count} 檔

👉 查看持股：{app_base}#holdings"""
    
    # LINE Push Message API payload
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(LINE_API, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            logger.info(f"成功发送通知给 {user_id}: {action}")
            return True
        else:
            logger.error(f"发送通知失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"发送通知异常: {e}")
        return False


def notify_stock_added(user_id: str, symbol: str, name: str, shares: float, avg_price: float, total_stocks: int):
    """新增持股通知"""
    details = f"股票：{symbol} {name}\n股數：{shares}\n均價：{avg_price}"
    return send_portfolio_update_notification(user_id, "✅ 新增持股", details, total_stocks)


def notify_stock_updated(user_id: str, symbol: str, name: str, updates: dict[str, Any], total_stocks: int):
    """更新持股通知"""
    update_items = []
    if "shares" in updates:
        update_items.append(f"股數：{updates['shares']}")
    if "avg_price" in updates:
        update_items.append(f"均價：{updates['avg_price']}")
    if "holding_bucket" in updates:
        bucket_name = "穩定獲利" if updates['holding_bucket'] == "stable_profit" else "短期持股"
        update_items.append(f"分類：{bucket_name}")
    
    details = f"股票：{symbol} {name}\n更新項目：{', '.join(update_items)}"
    return send_portfolio_update_notification(user_id, "🔄 更新持股", details, total_stocks)


def notify_stock_deleted(user_id: str, symbol: str, total_stocks: int):
    """删除持股通知"""
    details = f"股票：{symbol}"
    return send_portfolio_update_notification(user_id, "🗑️ 刪除持股", details, total_stocks)


def notify_portfolio_imported(user_id: str, success_count: int, failed_count: int, total_stocks: int):
    """匯入持股通知"""
    details = f"成功：{success_count} 筆"
    if failed_count > 0:
        details += f"\n失敗：{failed_count} 筆"
    return send_portfolio_update_notification(user_id, "📥 匯入持股", details, total_stocks)


def notify_screenshot_imported(user_id: str, success_count: int, failed_count: int, total_stocks: int):
    """截图匯入通知"""
    details = f"辨識成功：{success_count} 筆"
    if failed_count > 0:
        details += f"\n失敗：{failed_count} 筆"
    return send_portfolio_update_notification(user_id, "📷 截圖匯入", details, total_stocks)


def notify_portfolio_cleared(user_id: str):
    """清空持股通知"""
    details = "已清空所有持股"
    return send_portfolio_update_notification(user_id, "🧹 清空持股", details, 0)
