# FinOps Agent 架構與信任邊界

**Copilot SDK 是 Agent harness；Foundry Model 是可替換的模型來源，Foundry Agent Service 則是選配 hosting。** 本機可先切換模型，不需部署 Agent。Direct code deployment 不需要維護自訂 Dockerfile、sidecar 或 CLI TCP server；SDK 仍會自管其必要的 runtime process，並非完全移除了 runtime。

## 本機：先用現成工具分析，再讓 SDK 選擇工具

```mermaid
flowchart LR
    User["學員"] --> CLI["Python CLI"]
    CLI -->|"cost / departments / brief"| Tools["FinOpsToolbox"]
    Tools --> Evidence["Lab 1 mock evidence JSON"]
    Evidence -->|"學員手動附檔"| Chat["VS Code Copilot Chat / Ask"]
    Chat --> Decision["FinOps 決策摘要 / 待核准建議"]
    CLI -->|"ask / chat"| SDK["Copilot SDK / stdio runtime"]
    SDK --> Model["GitHub Copilot 或 BYOK model"]
    SDK -->|"explicit custom-tool allowlist"| Tools
    Tools --> Data["Synthetic billing / usage / mapping"]
    Tools --> Plan["ActionPlan + policy validation"]
    User -->|"console /approve + exact confirmation"| Approval["Human approval"]
    Plan --> Approval
    Approval --> Mock["Mock seat / budget mutation"]
    Mock --> Audit["In-memory audit"]
```

Lab 1 的現成 deterministic CLI 不載入 Copilot 或 Azure client；只需要 Python 與 fixture。`brief` 將既有報表工具輸出收集為 read-only JSON，學員再手動附到 VS Code Copilot Chat 分析。Lab 2 透過 `demo_connection.py` 將預建個人 tools 接到同一個 SDK harness。上圖的通用 CLI `ask` / `chat` 和 seat 操作是進階範例，不再是 Lab 2 必做。

## Lab 2：個人 FinOps 與管理者核准

```mermaid
flowchart LR
    U["User page / carol"] -->|"user capability"| ChatAPI["Demo chat API"]
    ChatAPI --> H["CopilotFinOpsHarness"]
    H --> T["get_my_costs / get_my_savings"]
    H --> R["request_budget_increase"]
    T --> D["BudgetDemo / scoped mock evidence"]
    R --> P["Pending request / limit still 20"]
    A["Admin page"] -->|"separate admin capability + human click"| Approve["ApprovalWorkflow"]
    P --> Approve
    Approve --> M["Mock budget: 20 -> 30"]
    M --> Refresh["User refresh: consumed 14 / remaining 16"]
    Refresh --> U
```

`BudgetDemo` 將 user 固定在伺服器端；model 沒有任意 username、plan payload 或 approve 參數。`get_my_costs` 只回傳 carol 的 billing、budget 與申請；`get_my_savings` 只使用她的 evidence。管理者核准是另一個 HTTP endpoint，不是 LLM tool。

`demo_server.py` 只綁 localhost，產生不同的 user/admin capabilities，以 request header 驗證；更改 UI role 不會繞過伺服器檢查。這是單一機器的角色扮演，並非 production 登入或多租戶 RBAC。持有 admin link 代表管理者，因此不要公布該連結或把頁面公開。

同一個 demo process 保留 SDK conversation、mock budgets、pending requests；頁面輪詢只讀這些資料，不重新呼叫模型。核准前不改額度，核准後不重設 consumed；重複核准不再次執行，過時的 budget snapshot 拒絕核准。退出程序後一切重設。

`demo.html` 沒有前端 build 或外部 CDN；「直接提交 mock 申請」是明確標示、不經模型的備援，不是默默替代 SDK 問答。Lab 3 模型切換沿用這個本機 UI；選配 Hosted 部署不包含 UI 或 approval API。

## Foundry Model：只替換推論來源

`FINOPS_MODEL_PROVIDER` 的三條路徑都由既有 `CopilotFinOpsHarness` 管理，沒有新增 Toolbox／MCP 連線。`copilot` 使用 `COPILOT_GITHUB_TOKEN`／`COPILOT_MODEL`，是 Lab 1/2 的 Azure-free 主線。Foundry 則統一讀取 `AZURE_OPENAI_ENDPOINT`／`MODEL_NAME`：key 模式另需 `AZURE_OPENAI_API_KEY`；identity 模式不用 key，透過非同步 bearer-token callback，在本機使用開發者憑證、Hosted 使用 Managed Identity。

Endpoint 可以是 resource/project 根網址，或已包含 `/openai/v1/` 的 base URL；harness 只補一次 v1 路徑。Hosted 的 `MODEL_NAME` 由 azd deployment 變數對應，未指定 endpoint 時保留平台注入的 project endpoint 作為來源。舊 key 設定僅用於相容遷移，不和部分新 key 設定混用。

切換 provider 不增加工具或擴大 user scope，模型仍不能核准。Process 啟動後不做 live model switch，需停止並重啟 demo；舊 conversation、mock requests 與角色 capabilities 不會延續。身分、連線錯誤會明確回報，不偷偷改用 Copilot。

GitHub billing fixture 是被分析的資料；Azure inference 是 Agent 自己產生的費用，兩者分開。`FINOPS_BACKEND=mock` 與 `FINOPS_ALLOW_REAL_WRITES=false` 在換模型時不變。

## Foundry：相同 harness，獨立 request state

```mermaid
flowchart LR
    Caller["學員 / 講師"] --> Endpoint["Foundry managed endpoint"]
    Endpoint --> Host["main.py / InvocationAgentServerHost"]
    Host --> Harness["CopilotFinOpsHarness"]
    Harness --> SDK["SDK auto-managed runtime"]
    SDK --> Model["預建 Foundry model"]
    Identity["Managed Identity"] --> Model
    SDK --> Tools["本次 invocation 的 FinOpsToolbox"]
    Tools --> Fixture["打包的 synthetic data"]
    Host --> Reply["reply + invocation_id + tool_calls"]
    Host --> Logs["Host / tool logs"]
```

`azure.yaml` 選擇 `host: azure.ai.agent`、`runtime: python_3_13`、`entryPoint: main.py`、`protocol: invocations`。YAML 的 `container.resources` 是平台執行資源大小，不表示需要另一個自建 container。

`main.py` 接收 `{"input":"..."}`，以同一個 local harness 完成呼叫，回傳 JSON。失敗／逾時回傳非成功 HTTP status，不會在 model error 後輸出 completed。每次 request 各自建立 session、toolbox 和 runtime state，完成後清理；這是簡化的 workshop 隔離方案，不提供跨 request memory 或 remote approval。

## 模型、資料、寫入權限分開

| 能力 | 認證／控制 | 不代表 |
| --- | --- | --- |
| Lab 2 使用者／管理者角色 | 本機啟動期不同 capabilities；核准需人點擊 | 正式 GitHub／Entra 登入或 real org 寫入權限 |
| Lab 1 Copilot Chat 分析 | VS Code 的 GitHub Copilot 登入、只附合成資料 | SDK 已完成接線或 GitHub org API 權限 |
| 個人 Copilot model calling | `COPILOT_GITHUB_TOKEN` | GitHub organization billing 管理權限 |
| BYOK model calling | API key 或 Managed Identity | Foundry hosting 已部署 |
| Real organization billing read adapter | instructor CLI、最小權限 token | 允許寫入 |
| Real write | write flag + payload policy + human approval | 模型能自己核准 |
| Foundry hosted sample | 每次請求獨立、固定 mock backend | production 多租戶授權或 durable audit |

Runtime 採 `mode="empty"`，只允許明確註冊的 custom tools；不讀取工作目錄的任意 hooks、skills 或 host Git 設定。GitHub billing/admin credential 不傳給 SDK child environment；model provider credential 與管理 API credential 是不同秘密。

## Approval 與資料生命週期

Lab 2 模型只提交提高限額申請；管理者頁面顯示 user、current → requested 與 reason，人點擊後才核准。進階 CLI 則用完整確認字串。Token 綁定 plan 指紋、有期限，對錯誤 token、過期 token 或改過的 plan 都拒絕；重複執行同一個有效 plan 不再次呼叫 backend。

Mock seats、budgets、plans、audit 都只存在目前程序。稽核事件記錄操作階段，不包含 tokens。真實遠端 API 的 exactly-once 與 distributed concurrency 並未由本範例保證；遠端回應遺失需人工核對，不能盲目重試。

## 費用與證據口徑

Synthetic files 是**內部 normalized schema**，不是可原封不動代入 GitHub API 的 response。Billing amount、net credits、原始 tokens 不能混為一談；fixture 單價為教學用，不是 GitHub 公告價格。

部門 mapping 是已解析的 cost-center/organizer 歸屬。Teams 可以重疊，不能直接當財務成本中心。無法歸屬的用量保留 `Unallocated`，含 real totals 與已知使用者報表之間的 residual。

Real billing endpoint 回傳的是報表，不是即時 meter；`retrieved_at` 不等於 provider 的資料更新時間。Usage metrics 只能支持採用率或效率假設，不應用來評分個人生產力，也不能保證 token 節省。

## 官方參考

- [Copilot SDK 與官方範例](https://github.com/github/copilot-sdk)
- [SDK isolation / multi-tenancy](https://github.com/github/copilot-sdk/blob/main/docs/setup/multi-tenancy.md)
- [SDK Foundry model provider / BYOK](https://github.com/github/copilot-sdk/blob/main/docs/auth/byok.md)
- [Foundry invocations adapter](https://learn.microsoft.com/azure/foundry/agents/how-to/add-protocol-adapter)
- [Foundry code deployment](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-deploy-own-code)
- [GitHub AI-credit billing usage](https://docs.github.com/en/rest/billing/usage)
- [Copilot usage report APIs](https://docs.github.com/en/rest/copilot/copilot-usage-metrics)
- [Seat management（文件標示 public preview）](https://docs.github.com/en/rest/copilot/copilot-user-management)
- [Budget API](https://docs.github.com/en/rest/billing/budgets)
- [User / organization budget 語意](https://docs.github.com/en/copilot/concepts/billing/budgets-for-usage-based-billing)

## 課程範圍

Lab 1 以成本、seats、UBB budgets、部門歸屬與節省建議為分析情境。本課程使用 mock tools、人工核准流程、Foundry model provider 與選配 direct-code hosting；不加入 Toolbox、檢索、正式 SSO、跨組織同步或即時帳務資料。
