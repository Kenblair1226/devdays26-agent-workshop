# 選配：部署到 Foundry Hosted Agent

先完成 Lab 1、Lab 2，並確認 Foundry 模型可以透過 SDK 回答問題。
只有主辦方已配好個人 hosting 環境、權限及 `starter/.azure/` 綁定，才操作這段。
尚未準備好就觀摩講師，不現場建立共用資源或反覆重試；課前要求見 [環境準備](environment-prep.md#lab-3-可用條件與-fallback)。

## 這次部署什麼？

`starter/azure.yaml` 使用 direct-code 設定：

```yaml
host: azure.ai.agent
codeConfiguration:
  runtime: python_3_13
  entryPoint: main.py
```

Foundry 執行 Python 程式，不需自己維護 Dockerfile。`main.py` 的 `InvocationAgentServerHost`
接收 `{"input":"..."}`，再呼叫 SDK harness。Hosted 的 `foundry-identity` 使用 Managed Identity 存取已部署模型。

**每次 invocation 都是獨立的 mock 狀態。** Lab 2 的網頁、管理者核准 API 和 repo 內的 IDE skills 不會變成雲端授權服務。
不要把本機 demo 當作正式登入或跨使用者的預算管理系統。

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

## 確認結果

回應應包含 `reply`、`invocation_id`、`tool_calls`、`backend=mock`。
對照課程資料及工具名稱；只有 HTTP `/readiness` 成功，不代表模型認證或呼叫成功。

`monitor` 預設讀近期 console logs，持續看才加 `--follow`；這不是完整 token trace。
部署或模型失敗要如實記錄，改看講師示範，不把觀摩說成自行部署完成。
Azure 推論與 hosting 費用另計，mock GitHub budget 不會限制它們。

課後由主辦方統一清理 Azure 資源。不要對共用 resource group 執行 `azd down`，
也不要提交 `.azure/`、認證、session history 或 audit logs。
