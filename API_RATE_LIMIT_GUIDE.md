# API Rate Limit 問題排查指南

## 問題現象

當系統出現 "Too many requests" 或相關錯誤訊息時，可能來自以下來源：

## 可能來源分析

### 1. Yahoo Finance API (yfinance)
- **特性**：免費公開 API，無需 token
- **限制**：有請求頻率限制，過於頻繁會被暫時封鎖
- **影響範圍**：
  - 持股價格查詢 (`/api/portfolio/prices`)
  - Agent 建議分析 (`/api/advisor/run`)
  - 股票資訊查詢

**判斷方式**：
- 錯誤訊息中包含 Yahoo Finance 相關字樣
- 同時分析多檔股票時出現
- 伺服器日誌顯示 yfinance 相關錯誤

**解決方案**：
1. 等待 5-10 分鐘後重試
2. 減少一次分析的持股數量
3. 增加 `REQUEST_DELAY` 參數（目前已調整為 1.0 秒）

### 2. Anthropic Claude API
- **特性**：需要 API token，有請求額度和頻率限制
- **限制**：
  - 免費額度有上限
  - 有 RPM (Requests Per Minute) 限制
  - 有 TPM (Tokens Per Minute) 限制
- **影響範圍**：
  - 截圖辨識功能 (`/api/screenshot`)
  - 台股大盤展望分析
  - Agent 操作建議生成

**判斷方式**：
- 錯誤訊息包含 "rate_limit_error"、"429"、"quota exceeded"
- 截圖辨識或 Agent 建議功能失效
- 伺服器日誌顯示 Anthropic API 錯誤

**解決方案**：
1. **檢查 API token 額度**：
   ```bash
   # 登入 Anthropic Console 檢查用量
   https://console.anthropic.com/
   ```

2. **檢查環境變數**：
   ```bash
   # 確認 .env 檔案中有正確的 token
   ANTHROPIC_API_KEY=sk-ant-...
   # 或
   CLAUDE_CODE_OAUTH_TOKEN=...
   ```

3. **暫時措施**：
   - 等待額度重置（通常按月或按日重置）
   - 減少使用截圖辨識功能
   - 暫時停用 Agent 建議功能

## 系統已實施的改進

### 1. 增強錯誤日誌記錄
- 詳細記錄錯誤類型和來源
- 區分 Yahoo Finance 和 Anthropic API 錯誤
- 提供具體的錯誤原因和建議

### 2. 調整請求間隔
- `REQUEST_DELAY` 從 0.5 秒增加到 1.0 秒
- 可在 `agents/holding_advisor_agent.py` 中進一步調整

### 3. 使用者友善的錯誤訊息
- 前端顯示具體錯誤原因
- 提供明確的解決建議
- 區分不同類型的 API 錯誤

## 伺服器日誌查看

```bash
# 查看即時日誌
docker-compose logs -f app

# 查看最近的錯誤
docker-compose logs app | grep -i "rate limit\|429\|too many"

# 查看特定時間範圍的日誌
docker-compose logs --since 1h app
```

## 預防措施

1. **分批處理持股**：
   - 建議單次分析不超過 10-15 檔股票
   - 大量持股可分多次分析

2. **避免頻繁操作**：
   - 不要在短時間內重複執行 Agent 建議
   - 截圖辨識建議間隔至少 5 秒

3. **監控 API 用量**：
   - 定期檢查 Anthropic API 使用量
   - 預留足夠的 API 額度

## 進階配置

如果仍然遇到 rate limit 問題，可以調整以下參數：

### 修改請求延遲時間

編輯 `agents/holding_advisor_agent.py`：

```python
# 目前設定為 1.0 秒，可增加到 1.5 或 2.0 秒
REQUEST_DELAY = 2.0
```

### 限制並發請求

目前系統已經是序列處理，但如果需要進一步限制，可以在 `app.py` 中添加請求限制中介軟體。

## 聯絡支援

如果問題持續存在：

1. **Anthropic API 問題**：
   - 聯絡 Anthropic 支援：https://support.anthropic.com/
   - 檢查服務狀態：https://status.anthropic.com/

2. **Yahoo Finance API 問題**：
   - 這是免費服務，暫時性限制通常會自動解除
   - 考慮使用其他股價資料來源作為備援
