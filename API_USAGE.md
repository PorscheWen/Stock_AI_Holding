# API 使用說明

## 新增功能

### 1. 持股匯出功能

#### GET /api/portfolio/export
匯出使用者的持股資料為 JSON 格式。

**Headers:**
```
X-User-ID: <user_id>
```

**Response:**
```json
{
  "stocks": [
    {
      "symbol": "2330.TW",
      "name": "台積電",
      "shares": 100,
      "avg_price": 580,
      "note": "核心持股"
    }
  ],
  "count": 1
}
```

**使用範例:**
```bash
curl -X GET http://localhost:5000/api/portfolio/export \
  -H "X-User-ID: U123456"
```

---

### 2. 持股匯入功能

#### POST /api/portfolio/import
從 JSON 資料匯入持股。

**Headers:**
```
X-User-ID: <user_id>
Content-Type: application/json
```

**Request Body:**
```json
{
  "stocks": [
    {
      "symbol": "2330.TW",
      "name": "台積電",
      "shares": 100,
      "avg_price": 580,
      "note": "核心持股"
    },
    {
      "symbol": "AAPL",
      "name": "蘋果",
      "shares": 50,
      "avg_price": 185,
      "note": "美股"
    }
  ],
  "clear_existing": false
}
```

**Parameters:**
- `stocks`: (必填) 持股陣列
- `clear_existing`: (選填) 是否清空現有持股，預設為 `false`

**Response:**
```json
{
  "success": 2,
  "failed": 0,
  "errors": []
}
```

**使用範例:**
```bash
curl -X POST http://localhost:5000/api/portfolio/import \
  -H "X-User-ID: U123456" \
  -H "Content-Type: application/json" \
  -d '{
    "stocks": [
      {
        "symbol": "2330.TW",
        "name": "台積電",
        "shares": 100,
        "avg_price": 580,
        "note": "核心持股"
      }
    ],
    "clear_existing": false
  }'
```

---

## 問題修復

### Too Many Requests 錯誤處理

**問題:**
當執行操作建議時，如果持股數量較多，可能會觸發 Yahoo Finance API 的請求頻率限制，導致 "too many requests" 錯誤。

**修復方案:**

1. **自動請求延遲**
   - 在每次 API 請求之間自動添加 0.5 秒延遲
   - 降低觸發 rate limit 的機率

2. **錯誤處理增強**
   - 自動識別 rate limit 錯誤 (HTTP 429, "too many requests", "rate limit")
   - 提供清晰的錯誤訊息和建議

3. **錯誤訊息範例**
   ```
   API 請求過於頻繁（AAPL），請稍後再試。
   建議：減少持股數量或等待數分鐘後重新執行。
   ```

**建議:**
- 如果持股數量超過 10 檔，建議分批執行操作建議
- 兩次操作建議執行之間，建議間隔至少 5 分鐘
- 可考慮使用匯出/匯入功能管理持股，避免重複新增

---

## 完整 API 端點列表

### 持股管理
- `GET /api/portfolio` - 取得持股列表
- `POST /api/portfolio` - 新增單一持股
- `DELETE /api/portfolio/<symbol>` - 刪除持股
- `DELETE /api/portfolio` - 清空所有持股
- `GET /api/portfolio/prices` - 取得持股即時價格
- `POST /api/screenshot/import` - 從截圖辨識匯入持股
- `GET /api/portfolio/export` - **新增** 匯出持股資料
- `POST /api/portfolio/import` - **新增** 匯入持股資料

### 操作建議
- `POST /api/advisor/run` - 執行操作建議分析
- `GET /api/advisor/latest` - 取得最新建議報告
- `GET /api/advisor/history` - 取得歷史建議列表

### 其他
- `GET /health` - 健康檢查
- `GET /app` - PWA 應用頁面
- `POST /api/screenshot` - 截圖分析

---

## 使用流程範例

### 1. 匯出持股備份
```bash
# 匯出持股
curl -X GET http://localhost:5000/api/portfolio/export \
  -H "X-User-ID: U123456" > portfolio_backup.json
```

### 2. 還原持股
```bash
# 匯入持股 (保留現有)
curl -X POST http://localhost:5000/api/portfolio/import \
  -H "X-User-ID: U123456" \
  -H "Content-Type: application/json" \
  -d @portfolio_backup.json

# 匯入持股 (清空現有)
curl -X POST http://localhost:5000/api/portfolio/import \
  -H "X-User-ID: U123456" \
  -H "Content-Type: application/json" \
  -d '{
    "stocks": [...],
    "clear_existing": true
  }'
```

### 3. 執行操作建議
```bash
# 執行分析
curl -X POST http://localhost:5000/api/advisor/run \
  -H "X-User-ID: U123456"

# 取得最新報告
curl -X GET http://localhost:5000/api/advisor/latest \
  -H "X-User-ID: U123456"
```
