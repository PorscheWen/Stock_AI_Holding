#!/usr/bin/env python3
"""
測試新功能的腳本
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"
TEST_USER_ID = "test_user_123"

def test_add_stock_with_name():
    """測試新增帶有名稱的持股"""
    print("📝 測試新增帶名稱的持股...")
    
    headers = {
        "Content-Type": "application/json",
        "X-User-ID": TEST_USER_ID
    }
    
    data = {
        "symbol": "2330.TW",
        "name": "台積電",
        "shares": 100,
        "avg_price": 580,
        "note": "測試用"
    }
    
    response = requests.post(f"{BASE_URL}/api/portfolio", headers=headers, json=data)
    print(f"   回應: {response.status_code}")
    print(f"   資料: {response.json()}")
    
    # 新增另一筆
    data2 = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "shares": 50,
        "avg_price": 185.5,
        "note": ""
    }
    
    response2 = requests.post(f"{BASE_URL}/api/portfolio", headers=headers, json=data2)
    print(f"   回應2: {response2.status_code}")
    print(f"   資料2: {response2.json()}")

def test_get_portfolio():
    """測試取得持股列表"""
    print("\n📊 測試取得持股列表...")
    
    headers = {"X-User-ID": TEST_USER_ID}
    
    response = requests.get(f"{BASE_URL}/api/portfolio", headers=headers)
    print(f"   回應: {response.status_code}")
    data = response.json()
    print(f"   持股數量: {len(data.get('stocks', []))}")
    
    for stock in data.get('stocks', []):
        print(f"   - {stock['symbol']}: {stock.get('name', '無名稱')} x {stock['shares']} @ {stock['avg_price']}")

def test_get_portfolio_with_prices():
    """測試取得帶價格的持股列表"""
    print("\n💰 測試取得帶價格的持股列表...")
    
    headers = {"X-User-ID": TEST_USER_ID}
    
    response = requests.get(f"{BASE_URL}/api/portfolio/prices", headers=headers)
    print(f"   回應: {response.status_code}")
    data = response.json()
    
    for stock in data.get('stocks', []):
        name = stock.get('name', '無名稱')
        symbol = stock['symbol']
        current = stock.get('current_price', 0)
        print(f"   - {symbol} ({name}): 現價 {current}")

def test_clear_portfolio():
    """測試清空持股"""
    print("\n🗑️  測試清空持股...")
    
    headers = {"X-User-ID": TEST_USER_ID}
    
    response = requests.delete(f"{BASE_URL}/api/portfolio", headers=headers)
    print(f"   回應: {response.status_code}")
    print(f"   資料: {response.json()}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Stock AI Holding - 功能測試")
    print("=" * 60)
    
    try:
        # 測試健康檢查
        print("\n❤️  測試健康檢查...")
        response = requests.get(f"{BASE_URL}/health")
        print(f"   回應: {response.status_code}")
        print(f"   資料: {response.json()}")
        
        # 測試新功能
        test_add_stock_with_name()
        test_get_portfolio()
        test_get_portfolio_with_prices()
        
        # 清理測試資料
        test_clear_portfolio()
        
        print("\n" + "=" * 60)
        print("✅ 所有測試完成！")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 錯誤: 無法連接到伺服器")
        print("   請確保 Flask 應用程式正在運行")
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
