# 📱 LINE 推送通知 - 快速參考卡

## 🎯 功能概述

每次持股更新時，自動推送 LINE 通知，包含更新內容和網頁連結。

## ⚡ 快速設定（3 步驟）

### 1️⃣ 取得 LINE Token
登入 [LINE Developers](https://developers.line.biz/) → 選擇 Channel → 複製 "Channel access token"

### 2️⃣ 設定環境變數
編輯 `.env`：
```bash
LINE_CHANNEL_ACCESS_TOKEN=your_token_here
APP_URL=https://your-domain.com/app
```

### 3️⃣ 重啟應用
```bash
python app.py
```

## 📊 支援的操作

| 操作 | API | 通知內容 |
|-----|-----|---------|
| ✅ 新增 | `POST /api/portfolio` | 代碼、名稱、股數、均價 |
| 🔄 更新 | `PATCH /api/portfolio/<symbol>` | 更新的欄位 |
| 🗑️ 刪除 | `DELETE /api/portfolio/<symbol>` | 股票代碼 |
| 📥 匯入 | `POST /api/portfolio/import` | 成功/失敗筆數 |
| 📷 截圖 | `POST /api/screenshot/import` | 辨識結果 |
| 🧹 清空 | `DELETE /api/portfolio` | 確認訊息 |

## 🧪 測試方法

### 使用測試腳本
```bash
python test_notification.py YOUR_LINE_USER_ID
```

### 使用 API
```bash
curl -X POST http://localhost:5000/api/portfolio \
  -H "Content-Type: application/json" \
  -H "X-User-ID: U1234567890abcdef" \
  -d '{"symbol":"2330.TW","name":"台積電","shares":100,"avg_price":580}'
```

## 📝 通知範例

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

## 🔍 常見問題

### Q: 沒收到通知？
✓ 確認 `LINE_CHANNEL_ACCESS_TOKEN` 已設定  
✓ User ID 是真實 LINE ID（不是 `pwa_` 開頭）  
✓ LINE Bot 已加為好友  
✓ 檢查伺服器日誌

### Q: 推送失敗？
✓ Token 是否過期  
✓ User ID 格式是否正確（`U` + 32字符）  
✓ 查看 LINE Developers Console 錯誤日誌

### Q: 網頁連結無法開啟？
✓ `APP_URL` 必須是 HTTPS  
✓ URL 必須包含 `/app`

## 📚 詳細文檔

- **完整說明**: [NOTIFICATION_GUIDE.md](NOTIFICATION_GUIDE.md)
- **功能總覽**: [NOTIFICATION_COMPLETE.md](NOTIFICATION_COMPLETE.md)
- **更新摘要**: [UPDATE_2026-05-20_NOTIFICATION.md](UPDATE_2026-05-20_NOTIFICATION.md)

## 🎨 自動過濾

- ✅ 僅推送給真實 LINE User ID
- ✅ 跳過本地測試 ID（`pwa_` 開頭）
- ✅ 未設定 Token 時優雅降級

## 🚀 部署到 Render

1. 在 Render Dashboard 設定環境變數
2. 添加 `LINE_CHANNEL_ACCESS_TOKEN`
3. 設定 `APP_URL` 為 `https://<服務名>.onrender.com/app`
4. 重新部署服務

## ⚙️ 技術細節

**模組位置**: `utils/notification.py`  
**API 超時**: 10 秒  
**日誌級別**: INFO  
**依賴套件**: `requests` (已在 requirements.txt)

## 💡 最佳實踐

1. 在生產環境使用環境變數管理 Token
2. 定期檢查 LINE API 使用配額
3. 監控推送失敗日誌
4. 為大量操作考慮批次通知合併

---

**快速連結**: 
- [GitHub Repo](https://github.com/PorscheWen/Stock_AI_Holding)
- [LINE Developers](https://developers.line.biz/)
- [Render Dashboard](https://render.com)
