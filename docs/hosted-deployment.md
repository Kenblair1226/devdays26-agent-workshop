# Lab 3（選配）：部署到 Foundry Hosted Agent

先完成 Lab 1、Lab 2；若做過 Lab 2 的 Foundry Model 選配，也要能分清本機 model switch 與 Hosted Agent deployment。
只有主辦方已配好個人 hosting 環境、權限及 `starter/.azure/` 綁定，才操作這段。
尚未準備好就觀摩講師，不現場建立共用資源或反覆重試；課前要求見 [環境準備](environment-prep.md#lab-3-hosted-agent-可用條件與-fallback)。

## 這次部署什麼？

`starter/azure.yaml` 使用 direct-code 設定：

```yaml
host: azure.ai.agent
codeConfiguration:
  runtime: python_3_13
  entryPoint: main.py
```

Foundry 執行 Python 程式，不需自己維護 Dockerfile。`main.py` 的 `FinOpsAgentServerHost`
組合 `InvocationAgentServerHost` 與 `ResponsesAgentServerHost`，同一個 process 提供兩種 protocol：

| 呼叫方式 | Protocol | 輸入與輸出 |
| --- | --- | --- |
| 原本的 JSON API | `invocations` | `{"input":"..."}` → `reply`、`invocation_id`、`tool_calls`、`backend` |
| Foundry Playground 聊天／Responses API | `responses` | 文字或文字 message list → Responses JSON，或 `stream=true` 的 SSE events |

兩者共用 SDK harness。Hosted 的 `foundry-identity` 使用 Managed Identity 存取已部署模型。
只接受非空白純文字，合併後上限 8,000 字元；不支援圖片、檔案或外部 tool results。
SSE 使用標準 Responses events，但目前 harness 完整回答後才送出文字，不是逐 token 串流。

**每次 invocation 都是獨立的 mock 狀態。** Lab 2 的網頁、管理者核准 API 和 repo 內的 IDE skills 不會變成雲端授權服務。
不要把本機 demo 當作正式登入或跨使用者的預算管理系統。
Responses 也只把本次 request 的文字交給新 harness，不載入過去 conversation 的訊息。
Playground 顯示聊天記錄不代表 agent 記得前一題；每題請提供完整條件，預算與核准狀態不跨 request 延續。

## 部署並送出範例問題

先用 `Ctrl+C` 停止本機 demo，再從 repo 根目錄執行。
使用附好的 `starter/request.example.json`，不用手動輸入 JSON。

PowerShell：

```powershell
Push-Location .\starter
$previousUserAgent = $env:AZURE_DEV_USER_AGENT
try {
    $env:AZURE_DEV_USER_AGENT = "microsoft_foundry_skill"
    azd deploy finops-agent --no-prompt
    if ($LASTEXITCODE -ne 0) { throw "Deploy failed; use instructor demo." }
    azd ai agent invoke --protocol invocations -f .\request.example.json
    if ($LASTEXITCODE -ne 0) { throw "Invoke failed; use instructor demo." }
    azd ai agent monitor
}
finally {
    $env:AZURE_DEV_USER_AGENT = $previousUserAgent
    Pop-Location
}
```

bash：

```bash
(
  cd starter &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy finops-agent --no-prompt &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent invoke --protocol invocations -f request.example.json &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent monitor
)
```

## 使用 Playground／Responses

若先前只部署 `invocations` 版本，需用上面的步驟重新部署，並在 Playground 選取支援
`responses` 的新版本（介面若提供 protocol 選項，選 `responses`），再建立新的聊天。
只修改本機 YAML 或只在舊 Playground 貼入 JSON，不會更新雲端 protocol。

也可從 `starter` 目錄用 CLI 明確選擇 Responses。PowerShell 可在上方 `try` 區塊內、
部署成功後加入：

```powershell
azd ai agent invoke --protocol responses "本月至今哪個部門消耗最多 AI credits？請列出金額、資料期間、來源與限制。"
if ($LASTEXITCODE -ne 0) { throw "Responses invoke failed; use instructor demo." }
```

bash（從 repo root 執行）：

```bash
(
  cd starter &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent invoke --protocol responses "本月至今哪個部門消耗最多 AI credits？請列出金額、資料期間、來源與限制。"
)
```

宣告兩個 protocols 後，CLI 預設選 `responses`。原本的 `request.example.json`
仍用 `--protocol invocations -f request.example.json`，其 request／response contract 不變。

## 確認結果

Invocations 回應應包含 `reply`、`invocation_id`、`tool_calls`、`backend=mock`。
Responses JSON 應有 `status=completed` 和 `output` 中的 assistant 文字；
SSE 應以 `response.completed` 結束。模型失敗或逾時時，Invocations 回傳 503／504；
Responses 回傳 `status=failed`／`response.failed`，不可把 HTTP 200 或收到 SSE 當作成功。
對照課程資料及工具名稱；只有 HTTP `/readiness` 成功，不代表模型認證或呼叫成功。

`monitor` 預設讀近期 console logs，持續看才加 `--follow`；這不是完整 token trace。
要先確認 Copilot runtime 的模型／工具 spans，可選做[本機 OpenTelemetry trace 檔](troubleshooting.md#選配本機-opentelemetry-trace-檔)；
它不需要新增服務，但 JSONL 不會自動顯示在 Foundry Traces，也不代表雲端 exporter 已接通。
Hosted manifest 現在明確設定 `FINOPS_OTEL_EXPORTER=azure-monitor`，以平台注入的
`APPLICATIONINSIGHTS_CONNECTION_STRING` 批次匯出 runtime spans 到既有 Application Insights。
部署前確認 project 已連結 Application Insights；若沒有，請先由資源擁有者設定，
或移除 manifest 的此項設定，只保留既有 host tracing。
這不新增 Azure 服務、不傳遞 connection string 給 runtime，也不啟用內容錄製。
`APPLICATIONINSIGHTS_AUTH_MODE=entra` 時使用 system-assigned Managed Identity，
需要對該 Application Insights 有既定的 telemetry 寫入權限；程式不自動授權。
在本次 session logs 找 `Copilot runtime trace export succeeded; spans=...`，
再以同一 trace ID 到 Portal 檢查 `chat ...`／`execute_tool ...`。
成功回答或成功匯出 log 不等於 Portal 已完成索引；查詢共用 telemetry 前須取得授權。
限制及故障處理見 [Hosted 批次匯出](troubleshooting.md#hosted批次匯出到-foundry-traces)。
部署或模型失敗要如實記錄，改看講師示範，不把觀摩說成自行部署完成。
Azure 推論與 hosting 費用另計，mock GitHub budget 不會限制它們。

課後由主辦方統一清理 Azure 資源。不要對共用 resource group 執行 `azd down`，
也不要提交 `.azure/`、認證、session history 或 audit logs。
