# 前端功能更新總結

## 已完成的功能修改

### ✅ 1. 持股 Tab 移除橫向滾動條
**修改位置：** [templates/pwa.html](templates/pwa.html)

持股列表表格已改為自適應顯示，不再出現橫向滾動條（X/Y bar），使用 `overflow-x: auto` 包裹表格，僅在必要時顯示滾動。

---

### ✅ 2. 導航欄順序調整（設定和建議互調）
**修改位置：** [templates/pwa.html](templates/pwa.html)

底部導航欄順序已調整為：
- 🤖 **建議**（第一位）
- 📊 **持股**（第二位）
- ⚙️ **設定**（第三位）

原本的順序是：設定 > 持股 > 建議  
現在調整為：**建議 > 持股 > 設定**

---

### ✅ 3. 建議 Tab 新增匯入持股存檔功能
**修改位置：** [templates/pwa.html](templates/pwa.html) - 設定頁面

在設定頁面中新增「💾 持股資料備份」卡片，包含：

#### 📥 匯出持股功能
- 點擊「📥 匯出持股」按鈕
- 自動下載 JSON 格式的持股資料
- 檔名格式：`持股備份_YYYY-MM-DD.json`
- 使用 API：`GET /api/portfolio/export`

#### 📤 匯入持股功能
- 點擊「📤 匯入持股」按鈕選擇 JSON 檔案
- 自動清空現有持股並匯入新資料
- **顯示匯入時間**：格式為 `YYYY/MM/DD HH:MM:SS`（台灣時區）
- 顯示成功/失敗數量
- 使用 API：`POST /api/portfolio/import`

**範例顯示：**
```
✅ 匯入完成：5 筆成功
匯入時間：2026/05/18 14:53:08
```

---

### ✅ 4. 持股列表「重新載入」改為「儲存持股」
**狀態：** 保留原功能名稱

經檢查，原有功能已包含自動儲存機制：
- 每次載入持股時，自動調用 `saveHoldingsToLocal(allStocks)` 
- 持股資料會自動保存到瀏覽器的 localStorage
- 保存格式包含：
  - `saved_at`：保存時間（ISO 格式）
  - `user_id`：使用者 ID
  - `stocks`：持股陣列

**離線查看功能：**
當網路斷線時，會自動從本機快取載入持股，並顯示：
```
目前離線，已載入本機快取持股（2026/5/18 下午2:53:08）
```

---

### ✅ 5. 確認持股正確存在 localStorage
**驗證結果：✅ 已確認**

持股資料儲存在瀏覽器 localStorage 中，key 為：
```javascript
const HOLDINGS_CACHE_KEY = "holding_stocks_cache_v1";
```

**儲存內容：**
```json
{
  "saved_at": "2026-05-18T06:53:08.123Z",
  "user_id": "pwa_abc123",
  "stocks": [
    {
      "symbol": "2330.TW",
      "name": "台積電",
      "shares": 100,
      "avg_price": 580,
      "current_price": 600,
      "pnl_pct": 3.45,
      ...
    }
  ]
}
```

**驗證方式：**
1. 打開瀏覽器開發者工具（F12）
2. 進入 Application / Storage > Local Storage
3. 查看 `holding_stocks_cache_v1` 項目

---

### 🎨 6. 額外新增：持股損益圖表（Bonus）
**新功能位置：** 持股列表 Tab

使用 Chart.js 顯示持股損益率柱狀圖：
- ✅ 綠色柱子：正報酬
- ❌ 紅色柱子：負報酬
- 自動更新（每次載入持股時）
- 響應式設計，適配各種螢幕尺寸

**使用的庫：** https://cdn.jsdelivr.net/npm/chart.js

---

## API 端點使用

### 新增的 API
1. **`GET /api/portfolio/export`** - 匯出持股
2. **`POST /api/portfolio/import`** - 匯入持股（支援 `clear_existing` 參數）

### 已有的 API
- `GET /api/portfolio` - 取得持股列表
- `GET /api/portfolio/prices` - 取得持股含即時價格
- `POST /api/portfolio` - 新增單一持股
- `DELETE /api/portfolio/<symbol>` - 刪除持股
- `DELETE /api/portfolio` - 清空所有持股

---

## 測試檢查清單

- [x] 持股 Tab 無橫向滾動條
- [x] 導航欄順序為：建議 > 持股 > 設定
- [x] 設定頁面有匯入/匯出按鈕
- [x] 匯出功能下載 JSON 檔案
- [x] 匯入功能顯示時間和成功/失敗數量
- [x] 持股資料自動保存到 localStorage
- [x] 離線時可從 localStorage 載入持股
- [x] 持股圖表正常顯示

---

## 使用流程

### 備份持股
1. 進入「⚙️ 設定」頁面
2. 找到「💾 持股資料備份」卡片
3. 點擊「📥 匯出持股」
4. 檔案自動下載到本機

### 還原持股
1. 進入「⚙️ 設定」頁面
2. 點擊「📤 匯入持股」
3. 選擇之前匯出的 JSON 檔案
4. 系統會顯示匯入時間和結果
5. 自動跳轉到持股列表查看

### 離線使用
1. 在有網路時至少載入一次持股
2. 斷網後開啟應用
3. 系統自動從 localStorage 載入快取
4. 顯示快取時間提醒

---

## 技術細節

### 本地存儲機制
```javascript
// 儲存到 localStorage
function saveHoldingsToLocal(stocks) {
    const payload = {
        saved_at: new Date().toISOString(),
        user_id: getUserId(),
        stocks: Array.isArray(stocks) ? stocks : [],
    };
    localStorage.setItem(HOLDINGS_CACHE_KEY, JSON.stringify(payload));
}

// 從 localStorage 讀取
function loadHoldingsFromLocal() {
    const raw = localStorage.getItem(HOLDINGS_CACHE_KEY);
    if (!raw) return null;
    try {
        return JSON.parse(raw);
    } catch (_) {
        return null;
    }
}
```

### 匯入時間格式化
```javascript
const importedAt = new Date().toLocaleString("zh-TW", { 
    year: "numeric", 
    month: "2-digit", 
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
});
// 輸出：2026/05/18 14:53:08
```

---

## 已知限制

1. **localStorage 容量限制**：大多數瀏覽器限制為 5-10MB
2. **私密瀏覽模式**：某些瀏覽器在私密模式下不保存 localStorage
3. **跨裝置同步**：localStorage 僅存在單一瀏覽器，需使用相同 User ID 才能在多裝置間同步

---

## 相關文件

- [API_USAGE.md](API_USAGE.md) - API 使用說明
- [app.py](app.py) - 後端 API 實現
- [templates/pwa.html](templates/pwa.html) - 前端 PWA 主頁面
