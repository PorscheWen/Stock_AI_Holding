# LINE 推送通知功能說明

## 功能概述

每次持股更新時，系統會自動向用戶的 LINE 帳號發送推送通知，包含：
- 📊 操作類型（新增/更新/刪除/匯入/清空）
- ⏰ 更新時間
- 📝 詳細內容（股票代碼、股數、均價等）
- 📈 目前持股總數
- 🔗 網頁連結（直接跳轉到持股頁面）

## 配置要求

### 1. 環境變數設定

在 `.env` 文件中設定以下變數：

```bash
# LINE Channel Access Token（必須）
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token

# PWA 完整網址（必須，須包含 https:// 和 /app）
APP_URL=https://your-domain.com/app
```

### 2. LINE Bot 設定

1. 登入 [LINE Developers Console](https://developers.line.biz/)
2. 創建或選擇現有的 Messaging API Channel
3. 在 "Messaging API" 頁籤找到 "Channel access token"
4. 將 Token 複製到 `.env` 文件的 `LINE_CHANNEL_ACCESS_TOKEN`

## 通知觸發時機

系統會在以下操作後自動發送通知：

### 1. ✅ 新增持股
- API: `POST /api/portfolio`
- 通知內容：股票代碼、名稱、股數、均價

### 2. 🔄 更新持股
- API: `PATCH /api/portfolio/<symbol>`
- 通知內容：股票代碼、更新項目（股數/均價/分類）

### 3. 🗑️ 刪除持股
- API: `DELETE /api/portfolio/<symbol>`
- 通知內容：已刪除的股票代碼

### 4. 📥 匯入持股
- API: `POST /api/portfolio/import`
- 通知內容：成功筆數、失敗筆數

### 5. 📷 截圖匯入
- API: `POST /api/screenshot/import`
- 通知內容：辨識成功筆數、失敗筆數

### 6. 🧹 清空持股
- API: `DELETE /api/portfolio`
- 通知內容：清空確認訊息

## 通知範例

```
📊 持股更新通知

操作：✅ 新增持股
時間：2026-05-20 14:30:00
股票：2330.TW 台積電
股數：100
均價：580.5
目前持股總數：5 檔

👉 查看持股：https://your-app.com/app#holdings
```

## 自動過濾機制

為避免不必要的推送，系統會自動過濾以下情況：

1. **未設定 LINE Token**：若未配置 `LINE_CHANNEL_ACCESS_TOKEN`，會記錄警告但不影響操作
2. **本地 User ID**：以 `pwa_` 開頭的本地 ID 不會發送通知（僅用於測試）
3. **LINE User ID**：只有真實的 LINE User ID 才會收到推送

## 測試方法

### 1. 確認配置

```bash
# 檢查環境變數
echo $LINE_CHANNEL_ACCESS_TOKEN
echo $APP_URL
```

### 2. 手動測試

使用 LINE User ID 進行操作：

```bash
# 新增持股
curl -X POST http://localhost:5000/api/portfolio \
  -H "Content-Type: application/json" \
  -H "X-User-ID: U1234567890abcdef" \
  -d '{"symbol":"2330.TW","name":"台積電","shares":100,"avg_price":580}'
```

### 3. 查看日誌

系統會記錄推送狀態：

```
INFO: 成功发送通知给 U1234567890abcdef: ✅ 新增持股
```

## 故障排除

### 問題 1: 沒有收到通知

**檢查項目：**
1. `LINE_CHANNEL_ACCESS_TOKEN` 是否正確設定
2. User ID 是否為真實 LINE User ID（不是 `pwa_` 開頭）
3. LINE Bot 是否已加為好友
4. 檢查伺服器日誌是否有錯誤訊息

### 問題 2: 推送失敗

**可能原因：**
1. Channel Access Token 過期或無效
2. User ID 不正確
3. LINE API 限制（每分鐘推送次數限制）

**解決方法：**
- 重新生成 Channel Access Token
- 確認 User ID 格式正確
- 查看 LINE Developers Console 的錯誤日誌

### 問題 3: 網頁連結無法開啟

**檢查項目：**
1. `APP_URL` 是否設定正確
2. URL 是否包含 `https://`
3. URL 是否以 `/app` 結尾

## 技術細節

### 模組架構

```
utils/
  └── notification.py        # 通知模組
      ├── send_portfolio_update_notification()  # 核心推送函數
      ├── notify_stock_added()                  # 新增通知
      ├── notify_stock_updated()                # 更新通知
      ├── notify_stock_deleted()                # 刪除通知
      ├── notify_portfolio_imported()           # 匯入通知
      ├── notify_screenshot_imported()          # 截圖通知
      └── notify_portfolio_cleared()            # 清空通知
```

### API 整合點

在 `app.py` 中，每個持股操作的 endpoint 都會調用對應的通知函數：

```python
from utils import notification

# 新增持股後發送通知
notification.notify_stock_added(uid, symbol, name, shares, avg_price, total_stocks)
```

## 擴展建議

1. **Rich Message 支持**：可升級為使用 Flex Message 提供更豐富的視覺效果
2. **通知設定**：允許用戶選擇開啟/關閉特定類型的通知
3. **批次通知合併**：大量操作時合併為單一通知，避免洗版
4. **推送延遲**：加入防抖機制，避免短時間內重複推送

## 相關文件

- [LINE Messaging API 文檔](https://developers.line.biz/en/docs/messaging-api/)
- [Push Message API](https://developers.line.biz/en/reference/messaging-api/#send-push-message)
- 專案 README.md
