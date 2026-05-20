# Stock_AI_Holding

獨立 **PWA**：首頁為 **Agent 操作建議**（一鍵分析、伺服器保留歷史）、紀錄持股、以 **截圖（Claude Vision）** 批次寫入，並可透過 **LINE Rich Menu** 切換畫面。後端為 **Flask**，可部署於 **Render**（見 `render.yaml`）。

## ✨ 最新功能（v2.1）

### 📱 LINE 推送通知 **NEW!**
- 每次持股更新自動推送 LINE 通知
- 包含操作類型、更新內容、持股總數
- 附帶網頁連結，點擊直接跳轉
- 支援新增、更新、刪除、匯入等所有操作
- 詳細說明：[NOTIFICATION_GUIDE.md](NOTIFICATION_GUIDE.md)

### 🎯 Tab 切換介面
- 持股管理頁面採用 Tab 設計，清晰分類功能
- **📋 持股列表**：查看所有持股，支援即時篩選
- **✍️ 手動新增**：手動輸入股票資訊
- **📷 截圖新增**：上傳券商截圖自動辨識

### 🔍 股票篩選功能
- 在持股列表輸入框即時篩選
- 支援按**股票代碼**或**股票名稱**搜尋
- 動態更新列表，無需重新載入

### 📝 股票名稱支援
- 資料庫新增股票名稱欄位
- 手動新增時可輸入股票名稱（選填）
- 截圖辨識自動提取股票名稱
- 持股列表顯示股票名稱，更易辨識

### 📂 整合截圖功能
- 截圖功能整合到持股管理頁面
- 支援點擊上傳或拖放上傳
- 優化的上傳區域 UI
- AI 辨識結果即時預覽

### 💾 跨裝置資料同步
- 所有資料依照 User ID 儲存
- 在設定頁面綁定 LINE User ID
- 相同 User ID 可在多裝置間同步持股資料
- 支援手機和電腦共用

## 線上環境（Render）

| 說明 | 網址 |
|------|------|
| 根路徑（JSON 導覽） | [https://stock-ai-holding.onrender.com/](https://stock-ai-holding.onrender.com/) |
| PWA | [https://stock-ai-holding.onrender.com/app](https://stock-ai-holding.onrender.com/app) |
| 健康檢查 | [https://stock-ai-holding.onrender.com/health](https://stock-ai-holding.onrender.com/health) |

部署後請將 **`APP_URL`** 設為 `https://stock-ai-holding.onrender.com/app`（Rich Menu 與 HTTPS 規定）。

## 功能

- **Agent 建議**：股價以 **Yahoo Finance（yfinance）** 公開 API 為主，**Stooq 日線 CSV** 交叉比對（可取得時）；紀錄 **建議日期／報價擷取時間（UTC）**、**整份 `advice_content` 與每檔內文** 至 `database/data/advisor_reports.json`（建議 Render **Persistent Disk** 掛載 `database/data`）  
- **持股管理**：
  - **手動新增**：輸入股票代碼、名稱、數量、成本等資訊
  - **截圖新增**：上傳券商持倉截圖，AI 自動辨識並匯入
  - **持股列表**：顯示所有持股含即時股價
  - **篩選功能**：按代碼或名稱即時搜尋
  - **管理操作**：單筆刪除、全部清空
- **使用者識別**：預設本機隨機 `X-User-ID`；可在「設定」貼上 **LINE User ID** 與其他裝置或 Bot 共用同一資料區  

## 快速開始（本機）

```bash
cd Stock_AI_Holding
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env
# 編輯 .env：ANTHROPIC_API_KEY、APP_URL（部署後須為 https://…/app）
python app.py
```

瀏覽器開啟：`http://127.0.0.1:5000/app`（根路徑 `/` 僅回傳 JSON 導覽，非 PWA 頁面。）

### 🎯 使用方式

#### 新增持股
1. 進入「持股」頁面
2. 選擇「✍️ 手動新增」或「📷 截圖新增」
3. **手動新增**：填寫股票代碼（必填）、名稱（選填）、數量、成本等
4. **截圖新增**：上傳券商 App 截圖，AI 自動辨識

#### 查看和管理持股
1. 在「📋 持股列表」Tab 查看所有持股
2. 使用篩選框搜尋特定股票
3. 點擊「刪」按鈕移除個別持股
4. 點擊「清空全部」移除所有持股

#### 跨裝置同步
1. 在第一台裝置記下 User ID（顯示在頁面頂部）
2. 在第二台裝置進入「⚙️ 設定」頁面
3. 輸入相同的 User ID 並儲存
4. 重新載入持股列表即可看到同步的資料

## Render 部署

1. 將此 repo 推上 GitHub，在 [Render](https://render.com) 建立 **Blueprint** 並選取含 `render.yaml` 的 repo，或手動建立 **Web Service**（Runtime：**Python 3**）。  
2. **Root Directory**：若 monorepo 才需填 `Stock_AI_Holding`；此 repo 為獨立專案則留空。  
3. **Build Command**：`pip install -r requirements.txt`  
   **Start Command**：`python app.py`（Render 會注入 `PORT`，`app.py` 已讀取。）  
4. **Environment**：於 Dashboard 設定與 `.env.example` 相同變數；`APP_URL` 在取得公開網址後設為 `https://<服務名>.onrender.com/app`（本 repo 預設服務名範例：`stock-ai-holding`）。  
5. **持久化**：免費方案重啟／重新部署後本機 JSON 可能清空；要長期保存持股檔請為該 Web Service 新增 **Persistent Disk**，掛載路徑設為 `database/data`（與 `portfolios.json` 所在目錄一致）。  

## LINE Rich Menu

1. 服務須為 **HTTPS**（如 Render），PWA 路徑為 `https://你的網域/app`。  
2. `.env` 設定 `LINE_CHANNEL_ACCESS_TOKEN` 與 `APP_URL`（完整含 `/app`）。  
3. 執行：

```bash
python setup_rich_menu.py
```

腳本會刪除舊選單、建立 **3×2** 選單圖、上傳並設為預設。六格對應：

| 建議 | 持股 | 截圖 |
|------|------|------|
| 設定 | 說明 | 回建議 |

（「回建議」與「建議」皆開 `#home`＝ Agent 建議首頁。）

## API（皆需標頭 `X-User-ID`）

| 方法 | 路徑 | 說明 | 推送通知 |
|------|------|------|---------|
| GET | `/api/portfolio` | 持股清單 | - |
| GET | `/api/portfolio/prices` | 持股 + 即時價 | - |
| POST | `/api/portfolio` | JSON：`symbol`, `shares`, `avg_price`, `note` | ✅ 新增持股 |
| PATCH | `/api/portfolio/<symbol>` | 更新持股資訊 | ✅ 更新持股 |
| DELETE | `/api/portfolio/<symbol>` | 刪除一檔 | ✅ 刪除持股 |
| DELETE | `/api/portfolio` | 清空 | ✅ 清空持股 |
| POST | `/api/screenshot` | `multipart/form-data` 欄位 `image` | - |
| POST | `/api/screenshot/import` | JSON：`{ "stocks": [...] }` | ✅ 截圖匯入 |
| POST | `/api/portfolio/import` | JSON：`{ "stocks": [...], "clear_existing": bool }` | ✅ 匯入持股 |
| POST | `/api/advisor/run` | 一鍵分析；股價來自 Yahoo（yfinance）並以 Stooq 比對；回傳含 `advice_date`、`quote_fetched_at`、`advice_content`（全文）、各檔 `advice_content`，並**儲存** | - |
| GET | `/api/advisor/latest` | 讀取最近一次儲存之建議（同上欄位） | - |
| GET | `/api/advisor/history?limit=10` | 建議歷史摘要（含 `advice_date`、`quote_fetched_at`、`has_full_text`） | - |

**推送通知說明**：標註 ✅ 的 API 會在操作成功後，自動向用戶的 LINE 發送推送通知（需設定 `LINE_CHANNEL_ACCESS_TOKEN`）。通知包含操作詳情和網頁連結。

## 目錄結構

```
Stock_AI_Holding/
├── app.py                 # Flask：PWA + API
├── render.yaml            # Render Blueprint（Web Service）
├── setup_rich_menu.py     # Rich Menu 部署
├── test_notification.py   # 推送通知測試腳本
├── Dockerfile, docker-compose.yml
├── config/settings.py
├── database/portfolio_db.py
├── database/advisor_store.py
├── agents/screenshot_agent.py
├── agents/holding_advisor_agent.py
├── utils/notification.py  # 推送通知模組
├── templates/pwa.html
├── static/manifest.json, sw.js
├── NOTIFICATION_GUIDE.md  # 推送通知完整說明
└── NOTIFICATION_COMPLETE.md  # 推送通知功能總覽
```

## 注意

- Rich Menu 的 **URI 必須 HTTPS**（LINE 規定）。  
- 截圖辨識需有效的 Anthropic API Key 或 OAuth Token。  
- **推送通知**：需設定 `LINE_CHANNEL_ACCESS_TOKEN`，用戶 ID 必須為真實 LINE User ID（本地 `pwa_` 開頭的 ID 不會推送）。詳見 [NOTIFICATION_GUIDE.md](NOTIFICATION_GUIDE.md)。
- 本專案與 `Stock_AI_MultiAgent` 分離；僅複用持股 DB 與截圖 Agent 邏輯。
