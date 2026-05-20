# 持股更新推送通知功能 - 更新摘要

**更新日期**: 2026-05-20

## ✨ 新增功能

### LINE 推送通知系統

每次持股更新時，系統會自動向用戶的 LINE 帳號發送即時通知，包含：
- 📊 操作類型和詳細內容
- ⏰ 更新時間戳記
- 📈 目前持股總數
- 🔗 直接跳轉網頁連結

## 📁 新增檔案

1. **`utils/notification.py`** - 推送通知核心模組
   - 整合 LINE Messaging API
   - 提供 6 種通知類型函數
   - 自動過濾機制（本地 ID、未設定 Token）

2. **`utils/__init__.py`** - Utils 套件初始化

3. **`NOTIFICATION_GUIDE.md`** - 完整功能說明文檔
   - 配置要求
   - 使用說明
   - 故障排除
   - 技術細節

## 🔧 修改檔案

### `app.py`
整合推送通知到所有持股操作 API：

1. **新增持股** (`POST /api/portfolio`)
   - 通知：股票代碼、名稱、股數、均價

2. **更新持股** (`PATCH /api/portfolio/<symbol>`)
   - 通知：更新項目（股數/均價/分類）

3. **刪除持股** (`DELETE /api/portfolio/<symbol>`)
   - 通知：已刪除的股票

4. **匯入持股** (`POST /api/portfolio/import`)
   - 通知：成功/失敗筆數

5. **截圖匯入** (`POST /api/screenshot/import`)
   - 通知：辨識結果統計

6. **清空持股** (`DELETE /api/portfolio`)
   - 通知：清空確認

## ⚙️ 環境變數要求

在 `.env` 檔案中設定：

```bash
# LINE 推送必要設定
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
APP_URL=https://your-domain.com/app
```

## 📱 通知範例

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

## 🎯 智慧過濾

- ✅ 僅發送給真實 LINE User ID
- ✅ 自動跳過本地測試 ID（`pwa_` 開頭）
- ✅ 未設定 Token 時優雅降級（記錄警告，不中斷操作）

## 🔍 驗證方式

### 快速測試

```bash
# 使用 LINE User ID 測試新增持股
curl -X POST http://localhost:5000/api/portfolio \
  -H "Content-Type: application/json" \
  -H "X-User-ID: U1234567890abcdef" \
  -d '{"symbol":"2330.TW","name":"台積電","shares":100,"avg_price":580}'
```

### 檢查日誌

```
INFO: 成功发送通知给 U1234567890abcdef: ✅ 新增持股
```

## 📚 相關文檔

- 詳細說明：[NOTIFICATION_GUIDE.md](NOTIFICATION_GUIDE.md)
- LINE API: https://developers.line.biz/en/docs/messaging-api/
- 專案說明：[README.md](README.md)

## 🚀 部署注意事項

1. 確保 `LINE_CHANNEL_ACCESS_TOKEN` 已在生產環境設定
2. `APP_URL` 必須使用 HTTPS 協議
3. LINE Bot 需先加為好友才能接收推送
4. 注意 LINE API 推送頻率限制

## ✅ 相容性

- ✅ 不影響現有功能
- ✅ 向後相容（未設定 Token 時不會中斷）
- ✅ 支援所有現有 API endpoint
- ✅ 日誌記錄完整

---

**技術支援**: 查看 NOTIFICATION_GUIDE.md 獲取完整故障排除指南
