#!/usr/bin/env python3
"""
測試 LINE 推送通知功能
用法：python test_notification.py [LINE_USER_ID]
"""
import sys
import os

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import notification


def test_notifications(user_id: str):
    """測試所有通知類型"""
    
    print("=" * 60)
    print("LINE 推送通知功能測試")
    print("=" * 60)
    print(f"測試 User ID: {user_id}\n")
    
    # 測試 1: 新增持股通知
    print("📝 測試 1: 新增持股通知")
    result = notification.notify_stock_added(
        user_id=user_id,
        symbol="2330.TW",
        name="台積電",
        shares=100,
        avg_price=580.5,
        total_stocks=5
    )
    print(f"   結果: {'✅ 成功' if result else '❌ 失敗'}\n")
    
    # 測試 2: 更新持股通知
    print("📝 測試 2: 更新持股通知")
    result = notification.notify_stock_updated(
        user_id=user_id,
        symbol="2330.TW",
        name="台積電",
        updates={"shares": 150, "avg_price": 575.0},
        total_stocks=5
    )
    print(f"   結果: {'✅ 成功' if result else '❌ 失敗'}\n")
    
    # 測試 3: 刪除持股通知
    print("📝 測試 3: 刪除持股通知")
    result = notification.notify_stock_deleted(
        user_id=user_id,
        symbol="2330.TW",
        total_stocks=4
    )
    print(f"   結果: {'✅ 成功' if result else '❌ 失敗'}\n")
    
    # 測試 4: 匯入持股通知
    print("📝 測試 4: 匯入持股通知")
    result = notification.notify_portfolio_imported(
        user_id=user_id,
        success_count=10,
        failed_count=2,
        total_stocks=14
    )
    print(f"   結果: {'✅ 成功' if result else '❌ 失敗'}\n")
    
    # 測試 5: 截圖匯入通知
    print("📝 測試 5: 截圖匯入通知")
    result = notification.notify_screenshot_imported(
        user_id=user_id,
        success_count=5,
        failed_count=0,
        total_stocks=19
    )
    print(f"   結果: {'✅ 成功' if result else '❌ 失敗'}\n")
    
    # 測試 6: 清空持股通知
    print("📝 測試 6: 清空持股通知")
    result = notification.notify_portfolio_cleared(user_id=user_id)
    print(f"   結果: {'✅ 成功' if result else '❌ 失敗'}\n")
    
    print("=" * 60)
    print("測試完成！請檢查您的 LINE 訊息")
    print("=" * 60)


def check_config():
    """檢查環境配置"""
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or os.getenv("CHANNEL_ACCESS_TOKEN", "")
    app_url = os.getenv("APP_URL", "")
    
    print("\n📋 環境配置檢查:")
    print(f"   LINE_CHANNEL_ACCESS_TOKEN: {'✅ 已設定' if token else '❌ 未設定'}")
    print(f"   APP_URL: {app_url if app_url else '❌ 未設定'}")
    print()
    
    if not token:
        print("⚠️  警告: 未設定 LINE_CHANNEL_ACCESS_TOKEN")
        print("   推送通知將不會實際發送")
        print("   請在 .env 檔案中設定此變數\n")
        return False
    
    return True


if __name__ == "__main__":
    # 檢查配置
    config_ok = check_config()
    
    # 取得 User ID
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    else:
        print("使用方法: python test_notification.py [LINE_USER_ID]")
        print("\n範例:")
        print("  python test_notification.py U1234567890abcdef")
        print("\n若要測試本地 ID (不會實際推送):")
        print("  python test_notification.py pwa_test123\n")
        
        user_id = input("請輸入 LINE User ID (或按 Enter 使用測試 ID): ").strip()
        if not user_id:
            user_id = "pwa_test_local"
            print(f"使用測試 ID: {user_id}\n")
    
    # 執行測試
    if config_ok or user_id.startswith("pwa_"):
        test_notifications(user_id)
    else:
        print("❌ 請先設定 LINE_CHANNEL_ACCESS_TOKEN 後再執行測試")
        sys.exit(1)
