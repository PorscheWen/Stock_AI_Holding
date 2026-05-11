# Stock_AI_Holding

獨立 **PWA**：紀錄與瀏覽股票持股、以 **截圖（Claude Vision）** 批次寫入持股，並可透過 **LINE Rich Menu** 以 URI 切換同一 PWA 畫面（`#home` / `#holdings` / `#screenshot` 等）。後端為 **Flask**，可部署於 **Render**（見 `render.yaml`）。

## 線上環境（Render）

| 說明 | 網址 |
|------|------|
| 根路徑（JSON 導覽） | [https://stock-ai-holding.onrender.com/](https://stock-ai-holding.onrender.com/) |
| PWA | [https://stock-ai-holding.onrender.com/app](https://stock-ai-holding.onrender.com/app) |
| 健康檢查 | [https://stock-ai-holding.onrender.com/health](https://stock-ai-holding.onrender.com/health) |

部署後請將 **`APP_URL`** 設為 `https://stock-ai-holding.onrender.com/app`（Rich Menu 與 HTTPS 規定）。

## 功能

- **持股**：新增、列表（含即時股價）、單筆刪除、全部清空  
- **截圖**：上傳券商持倉截圖 → 辨識 → 一鍵寫入 `database/data/portfolios.json`  
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

| 首頁 | 持股 | 截圖 |
|------|------|------|
| 設定 | 說明 | 回首頁 |

（「回首頁」與「首頁」皆開 `#home`，方便從說明頁一鍵返回。）

## API（皆需標頭 `X-User-ID`）

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/portfolio` | 持股清單 |
| GET | `/api/portfolio/prices` | 持股 + 即時價 |
| POST | `/api/portfolio` | JSON：`symbol`, `shares`, `avg_price`, `note` |
| DELETE | `/api/portfolio/<symbol>` | 刪除一檔 |
| DELETE | `/api/portfolio` | 清空 |
| POST | `/api/screenshot` | `multipart/form-data` 欄位 `image` |
| POST | `/api/screenshot/import` | JSON：`{ "stocks": [...] }` |

## 目錄結構

```
Stock_AI_Holding/
├── app.py                 # Flask：PWA + API
├── render.yaml            # Render Blueprint（Web Service）
├── setup_rich_menu.py     # Rich Menu 部署
├── Dockerfile, docker-compose.yml
├── config/settings.py
├── database/portfolio_db.py
├── agents/screenshot_agent.py
├── templates/pwa.html
└── static/manifest.json, sw.js
```

## 注意

- Rich Menu 的 **URI 必須 HTTPS**（LINE 規定）。  
- 截圖辨識需有效的 Anthropic API Key 或 OAuth Token。  
- 本專案與 `Stock_AI_MultiAgent` 分離；僅複用持股 DB 與截圖 Agent 邏輯。
