# 學員手冊：打造 Copilot FinOps Agent

**90 分鐘，3 個 Labs。** 你會先建立本機 FinOps tools，再把 tools 接入 Copilot SDK，最後視環境狀況部署到 Foundry。學員只編輯 `starter/`；`solution/` 是答案。

## 情境與成果

你是虛構組織 `octo-demo` 的平台工程師。主管問：「本月至今，哪個部門消耗最多 AI credits？主要花在哪些模型？可以怎麼節省？」

完成後，你的 Agent 能查費用、分部門與模型分析、提出有依據的建議，並把 seat / budget 變更交給人核准。**本機程式不等於離線 LLM**：Lab 1 不需認證；Lab 2 的模型問答需要個人 Copilot 使用權限或主辦方 BYOK，但不需要 Foundry hosting 資源。

| 時間 | 活動 | 完成證據 |
| --- | --- | --- |
| 0–8 分 | 情境、架構與安全界線 | 分辨 model runtime、tools、hosting |
| 8–15 分 | 啟動課前環境 | 本機 `cost` 成功 |
| 15–37 分 | Lab 1：FinOps tools | 部門排行含未歸屬用量 |
| 37–63 分 | Lab 2：Copilot SDK harness | 自然語言問答與人工核准 |
| 63–78 分 | Lab 3：Foundry | 自行部署或觀摩同一程式的 demo |
| 78–86 分 | 講師延伸示範與討論 | 資料、權限、觀測的限制 |
| 86–90 分 | 成果核對、清理 | 關閉程序、移除認證 |

## 開始前

先完成 [環境準備](environment-prep.md)。以下命令從 **repository root** 執行。PowerShell 使用 `\`；bash 使用 `/`。不要在同一個 Python process 混載 starter 與 solution。

PowerShell 7：

```powershell
& .\starter\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
python -m finops_agent --data-dir .\data cost
```

bash：

```bash
source starter/.venv/bin/activate
export PYTHONPATH="$PWD/starter/src"
export FINOPS_BACKEND=mock
python -m finops_agent --data-dir data cost
```

範例固定在 **2026-09-03 UTC** 的 snapshot；`month_to_date` 是 9 月 1–3 日，不是你執行當天。應看到 `net_quantity=4760`、`net_amount=44.88`、`currency=USD`。這些是**合成教學數字**，不是正式 GitHub 價格、invoice 或原始 token 數。

## Lab 1：建立 FinOps tools（22 分鐘）

### 1. 看懂資料來源（4 分鐘）

閱讀 `data/ai-credit-usage.json`、`data/department-mapping.json` 與 `data/users-28-day.ndjson`。

| 資料 | 可回答 | 不能直接推論 |
| --- | --- | --- |
| Billing snapshot | 本期 gross/net credits 與金額 | Prompt token 明細、最終 invoice |
| 已解析的部門 mapping | 使用者歸屬與部門排行 | GitHub team 自動等於財務部門 |
| Usage metrics | 採用情形與可改善的假設 | 員工生產力、保證節省百分比 |
| Seats / budgets | 指派、預算與限制 | 沒有 activity 就一定沒有使用 |

財務部門由主辦方預先解析 cost center 或明確 mapping；多個 team 不重複加總。未能歸屬的資料留在 `Unallocated`。

### 2. 先看到未完成的 checkpoint（2 分鐘）

```powershell
python -m pytest .\starter\checks\test_lab1.py -q
```

bash 把路徑改成 `starter/checks/test_lab1.py`。未完成時應失敗，這不是環境故障。

### 3. 完成部門 aggregation（10 分鐘）

編輯 `starter/src/finops_agent/analytics.py`，找到 `TODO(Lab 1)` 的 `rank_departments()`。它接收已解析的 `ReportingPeriod`，你只需聚合，不必呼叫網路。

1. 用 `self._records(period)` 取得該期間的資料。
2. 用既有 `self._department(item)` 決定歸屬；它處理大小寫、unknown user 與 residual。
3. 累加 `net_quantity`、`net_amount`，用 set 計算每部門不同使用者數；`user=None` 的 residual 不算一個人。
4. 依用量遞減、部門名稱遞增排序，給予 1-based rank。
5. 先從完整 rows 計算未歸屬用量，再回傳 `rows[:limit]`。
6. 以 `**self._context()` 保留 `as_of`、`currency`、`unit` 和來源；另加 `period` 與歸屬限制。保留既有 `self._validate_limit(limit)`。

可讓 Copilot 協助，但先把限制寫清楚：

> 完成 rank_departments，使用既有資料模型與 period 篩選；不得呼叫網路、不得丟棄 Unallocated，且不可把同一使用者在同部門的多筆資料算成多個人。先閱讀 test_lab1 的預期，再解釋演算法。

參考答案是 `solution/src/finops_agent/analytics.py` 的同名方法；介面保持一致。不要讓 Copilot 把測試改成接受錯誤答案。

### 4. 檢視結果與其他 tools（6 分鐘）

```powershell
python -m pytest .\starter\checks\test_lab1.py -q
python -m finops_agent departments
python -m finops_agent breakdown --dimension model
python -m finops_agent forecast 80
python -m finops_agent budgets
```

| Checkpoint | 預期 |
| --- | --- |
| MTD net credits / amount | 4,760 / USD 44.88 |
| 部門第一名 | AI Lab，2,400 / USD 26 |
| Unallocated | 90 credits |
| 模型第一名 | gpt-5.4，2,580 credits |
| `forecast 80` | 約 USD 448.80 的月末 run-rate 情境 |

Forecast 是把短期平均外推的**假設**，不是保證花費，也不是把 license fees 加總後的總帳單。Budget 的 remaining 應看該 budget 自己的 `consumed_amount` 與 scope，不能拿另一個期間或另一個口徑硬減。

**思考題：** 沒有回傳某日資料，代表零花費還是資料不足？為何 credit 用量最高的部門不一定是浪費最多的部門？

## Lab 2：整合 Copilot SDK harness（26 分鐘）

### 1. 理解 harness 與 tool contract（5 分鐘）

閱讀 `starter/src/finops_agent/harness.py` 和 `sdk_tools.py`。真正的流程是：

```text
你的問題 -> Copilot SDK session -> 模型選擇 custom tool
        -> Python handler -> 結構化 evidence -> 模型回答
```

`CopilotClient(mode="empty")` 由 SDK 管理自己的 runtime；**不用 Docker、sidecar 或手動 `copilot --headless`**。`available_tools` 是明確 allowlist，未知工具與 shell / 檔案操作不在授權範圍。`approve_action` 永遠不交給模型。

### 2. 完成 instructions 與兩個 registrations（9 分鐘）

執行 `python -m pytest starter/checks/test_lab2.py -q`，先看到失敗。

編輯 `starter/src/finops_agent/instructions.py` 的 `TODO(Lab 2)`，要求：

- 所有費用與帳號數字必須引用 tools；缺資料就說明限制。
- 回答包含 period、as-of 或 retrieved-at、currency/unit；不把 snapshot 說成即時。
- 區分 AI credits、原始 tokens、USD、license fees 與 Azure inference 費用。
- 最佳化建議要有 evidence、假設與品質衡量方式，不保證節省比例。
- Agent 只能先提出 plan；核准必須來自模型之外的人。

接著在 `starter/src/finops_agent/sdk_tools.py` 的兩個 `TODO(Lab 2)` 補上 `rank_department_consumption`、`plan_action`。其餘工具與 schema helpers 已提供。

```python
_tool(
    "rank_department_consumption",
    "Rank departments by AI-credit consumption.",
    period_schema,
    lambda args: toolbox.rank_department_consumption(**args),
),
```

`plan_action` 的參數為 `kind`、`target`、`payload`；kind 僅允許 `assign_seats`、`remove_seats`、`create_budget`、`update_budget`。仿照 solution 的 schema，但**不加入核准工具、actor 或任意 shell 命令**。

重跑 checkpoint。它除了檢查名字，也會呼叫 handler、核對資料與拒絕未核准的變更。

### 3. 用自然語言查費用（5 分鐘）

先完成 [Lab 2 認證](environment-prep.md#lab-2-模型認證)。模型使用個人 Copilot 或主辦方 BYOK；不要提供 org admin token。

```powershell
python -m finops_agent ask "本月至今哪個部門消耗最多 AI credits？請附資料期間、來源與限制。"
python -m finops_agent ask "分析模型用量，提供三個節省 context/token 的實驗建議，不要捏造節省百分比。"
```

答案文字可能不同，但 evidence 應一致。建議可包括縮小任務、只提供相關 context、任務切換時開新 session、用低成本模型處理簡單任務，並以品質／完成率衡量。現有報表沒有原始 token 明細，不能從 credits 直接換算 tokens。

### 4. 人工核准 seat / budget（7 分鐘）

```powershell
python -m finops_agent chat
```

在同一個 chat 中依序操作：

1. 輸入：「請規劃把 judy 的 seat 設為 pending cancellation，先不要執行。」
2. 輸入 `/plans`，取得 plan ID 並檢視目標、payload。
3. 輸入 `/approve PLAN_ID`，先輸入 `no`；確認狀態仍未核准。
4. 再輸入 `/approve PLAN_ID`，確認內容後依提示輸入完整 `APPROVE PLAN_ID`。
5. 輸入 `/audit`，再問：「重新列出 seats，judy 現在是什麼狀態？」
6. 以「為 carol 建立 USD 30 的 user AI-credit budget、hard stop=true」重複同一流程；最後 `/quit`。

`/approve` 是**本機 console 指令**，不是發給模型的 prompt。它先顯示完整 plan，才核准及執行；approval token 不送進模型、不列在 audit。Mock 狀態只在這個程序存活，不會影響 GitHub。

若時間不足，可用無模型的 `python -m finops_agent approval-demo` 與 `approval-demo --action budget` 練習人工確認。`--rehearse` 僅供講師自動彩排，輸出明確標記 simulated；不能當真人核准證據。

**Checkpoint 2：** Agent 能呼叫工具回答，未核准動作被拒絕，人確認後 mock 狀態改變且留下 audit；不是只看終端印出「success」。

## Lab 3：部署到 Foundry Agent Service（15 分鐘，可改 Demo）

第 63 分鐘由講師宣布 hands-on 或 demo。若沒有預建資源、時間不足或部署等候超過 5 分鐘，**不要現場建立 Azure 基礎設施**，改看講師既有環境。

### 1. 了解部署內容

`starter/azure.yaml` 的 agent service 使用：

```yaml
host: azure.ai.agent
codeConfiguration:
  runtime: python_3_13
  entryPoint: main.py
```

`main.py` 的 `InvocationAgentServerHost` 接收 `{"input":"..."}`，直接呼叫同一個 SDK harness。Foundry 管理運算資源；沒有自訂 Dockerfile。模型採 `FINOPS_MODEL_PROVIDER=foundry-identity`，透過 Managed Identity 存取已部署模型。

Hosted 範例為 **每次 invocation 獨立的 mock 問答／planning**，不共享聊天紀錄或核准狀態。人工核准與真實寫入留在本機講師流程，這不是 production approval service。

### 2. 部署與呼叫

確認主辦方已在你的 `starter/.azure/` 綁定**個人**環境，且前兩個 checkpoints 已完成。使用 repo 附的 `starter/request.example.json`，避免 PowerShell JSON quoting 與 BOM 問題。

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

bash（subshell 結束即回原目錄）：

```bash
(
  cd starter &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy finops-agent --no-prompt &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent invoke --protocol invocations -f request.example.json &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent monitor
)
```

回應含 `reply`、`invocation_id`、`tool_calls`、`backend=mock`。對照 Lab 1 的數字；在 monitor 查看相同 invocation 的 tool 名稱。Monitor 預設取近期 console logs；`--follow` 才是持續串流。完整 distributed tracing 需課前另行配置，console logs 不等於完整模型 token trace。

### 3. Checkpoint 與切換 Demo

自行完成 deploy / invoke，或在講師 demo 中指出 source entry point、Managed Identity、tool call 與 evidence，皆符合 Lab 3 的教學目標。無資源時不要把本機結果宣稱為「已部署 Foundry」。

## 落後時的 checkpoint recovery

從 repository root 執行，工具會先備份你的編輯到被 Git 忽略的 `.workshop-backups/`，只還原對應 lab 的檔案：

```powershell
python .\scripts\checkpoint.py --lab 1
python .\scripts\checkpoint.py --lab 2
python -m pytest .\starter\checks -q
```

bash 使用 `python scripts/checkpoint.py --lab 1`。不刪整個工作目錄、不覆蓋 `.env`，也不需要清除自己的 Git 變更。

## 最後清理

退出 chat、停止本機 host，清除 shell 認證；不要提交 `.env`、真實資料、runtime history 或 audit log。主辦方統一關閉 workshop Azure 資源；學員不要對共用 resource group 執行 `azd down`。

```powershell
Remove-Item Env:COPILOT_GITHUB_TOKEN,Env:FOUNDRY_API_KEY -ErrorAction SilentlyContinue
```

bash：`unset COPILOT_GITHUB_TOKEN FOUNDRY_API_KEY`。若曾用課程專用短期 token，課後在 GitHub 撤銷。
