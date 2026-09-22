# 環境準備與課前檢查

**課前完成安裝與認證**，讓現場可以專心實作。課程依序進行用量調查、本機額度申請與人工核准；Foundry 模型切換是 Lab 2 選配，Hosted Agent 部署是 Lab 3 選配。

## 主辦方：Foundry 環境及 Github copilot 授權

![](images/Screenshot%202026-09-21%20173518.png)

![](images/Screenshot%202026-09-21%20173544.png)

![](images/Screenshot%202026-09-21%20173603.png)

![](images/Screenshot%202026-09-21%20173726.png)


## 學員必要環境

| 項目 | Lab 1 | Lab 2 | Lab 3 |
| --- | --- | --- | --- |
| Git、VS Code、Python 3.13、repo | 必要 | 必要 | 必要 |
| VS Code Copilot Chat 登入／使用權限 | Agent 唯讀 terminal 調查；Ask 作逐次貼結果的備案，選做 dashboard 建檔 | 可作開發輔助 | 不影響 hosting |
| Copilot SDK 與其 pinned runtime | 報表工具不需要 | 必要 | Hosted Agent runtime 使用 |
| 瀏覽器與可用的 localhost port | 選做 dashboard 用瀏覽器開本機檔案，不佔 port | 8098，User/Admin 兩分頁 | 依主辦方環境 |
| 個人 Copilot token 或主辦方 BYOK | 不需要 | 模型問答時需要；選配 Foundry provider | Hosted 使用 Managed Identity |
| Azure CLI 登入或模型 key | 不需要 | Copilot 主線不需要；選配 Foundry Model 需其一 | 部署及 remote invocation 需課前權限 |
| azd ≥1.27.1、Foundry extension、hosting 環境 | 不需要 | 不需要 | 選配 Hosted 部署才需要 |
| 預建 Foundry project、model、RBAC | 不需要 | Copilot 主線不需要 | 個人配發的環境，或講師 demo |

Lab 1 的現成 deterministic CLI（包含 `trend`、`roster`、`workflows`、`options`）只讀 mock fixtures，不載入 SDK／Azure client；設好 `PYTHONPATH` 後連 `python -S -m finops_agent --data-dir data trend` 也可執行。Copilot Chat 仍需既有 GitHub 登入，但不需 SDK token。完整 `brief` 留到分析／選擇後才匯出。Lab 2 是**在本機執行 harness**，不是 LLM 離線運行。使用 GitHub Copilot 模型時會消耗自己的 Copilot 額度；BYOK 的 inference 費用由 Azure/model provider 計費。這與範例中被分析的 GitHub billing data 是不同帳。

## 安裝（repository root）

第一次 clone 後要在自己的電腦建立 `.venv/`。以下從 repo 根目錄執行，先確認是 **Python 3.13.x**；版本不對或建立失敗時先修正，不要直接執行啟用指令。

Windows 建議 PowerShell 7；執行政策不允許 activation 時，直接使用 `.\starter\.venv\Scripts\python.exe` 執行後續的 `-m pip` 和 `-m finops_agent`，不要永久放寬系統政策。已經做完安裝的人，之後只需啟用原本的環境。

PowerShell：

```powershell
python --version
python -m venv .\starter\.venv
& .\starter\.venv\Scripts\Activate.ps1
python -m pip install -r .\starter\requirements.txt
python -m copilot download-runtime
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
$env:FINOPS_ALLOW_REAL_WRITES = "false"
python -m finops_agent --data-dir .\data cost
```

bash：

```bash
python3.13 --version
python3.13 -m venv starter/.venv
source starter/.venv/bin/activate
python -m pip install -r starter/requirements.txt
python -m copilot download-runtime
export PYTHONPATH="$PWD/starter/src"
export FINOPS_BACKEND=mock
export FINOPS_ALLOW_REAL_WRITES=false
python -m finops_agent --data-dir data cost
```

預期輸出：MTD net `34906.67` AI credits、`329.12` USD、snapshot `2026-09-22T23:59:59Z`，期間為 **2026-09-01～2026-09-22**。全部預先模擬，不是實測或真實帳單。`starter/tests` 與 `starter/checks/test_lab1.py` 應開箱即通過；只有 Lab 2 checks 在完成 SDK TODO 前會失敗。

## Lab 1 Copilot Chat 準備

在 VS Code 開啟 **repo 根目錄**，登入 Copilot 並選 **Agent 模式**。依 [學員手冊](student-lab.md) 使用本專案的 [調查 skill `/finops-investigation`](../.github/skills/finops-investigation/SKILL.md)，由 skill 提供工具目錄與逐步調查指令；不先附完整 evidence、教師答案或跑 `options`。

Agent 使用前面已初始化的 terminal；新 terminal 只需啟用既有 venv、重設 `PYTHONPATH`、`FINOPS_BACKEND=mock` 與 `FINOPS_ALLOW_REAL_WRITES=false`。

找不到 skill 時，在 Chat 輸入 `/skills` 開啟 Configure Skills，確認 `chat.useAgentSkills` 已啟用（目前預設 true）；也可直接輸入 `/finops-investigation` 或 `/finops-dashboard`。仍不可用就附上對應 `SKILL.md`，請 Agent 手動遵循；無須全域安裝、個人 Skill Manager 或額外 extension。詳見 [疑難排解](troubleshooting.md)。

`trend` 使用獨立 **2026-08-01～2026-08-22** 比較期，普通 billing `previous_month` 不支援。缺案例檔請找 TA，不補零或捏造資料。若 Agent／terminal tools 不可用，由人執行下一個唯讀命令、逐次貼給 Ask。

### 選做 dashboard 的準備

完成決策摘要後，用 `python -m finops_agent --data-dir data brief --include-investigation --output workshop-output/lab1-evidence.json` 匯出；已存在就換新名稱。一般 `brief` 不預載調查脈絡。接著輸入 `/finops-dashboard 用 workshop-output/lab1-evidence.json 製作本機 dashboard`；[dashboard skill](../.github/skills/finops-dashboard/SKILL.md) 提供單一 HTML、資料驗證與 Clawpilot 樣式規則。

檢視 edits 後才接受、手動開啟，以 File API 選取 evidence；不改 source／`.env`，不新增依賴、CDN、網路、server 或管理操作。瀏覽器不需模型憑證；若 `file://` 載入失敗，修正選檔方式而不是開服務。選做不影響 Checkpoint 1，未完成仍可進 Lab 2。

## Lab 2 模型認證

### 方式 A：個人 GitHub Copilot（本機主線）

依 [SDK authentication](https://docs.github.com/en/copilot/how-tos/copilot-sdk/auth/authenticate) 建立活動用 fine-grained PAT，授予 **Account permissions → Copilot Requests → Read-only**，並確認帳號及組織政策允許 Copilot SDK 使用。

用隱藏輸入避免把 token 留在 shell history：

```powershell
$env:FINOPS_MODEL_PROVIDER = "copilot"
$env:COPILOT_GITHUB_TOKEN = Read-Host "Workshop Copilot token" -MaskInput
$env:COPILOT_MODEL = "gpt-6-astra"
python -m finops_agent ask "目前本月的範例費用是多少？"
```

```bash
export FINOPS_MODEL_PROVIDER=copilot
read -rsp "Workshop Copilot token: " COPILOT_GITHUB_TOKEN; printf '\n'
export COPILOT_GITHUB_TOKEN
export COPILOT_MODEL=gpt-6-astra
python -m finops_agent ask "目前本月的範例費用是多少？"
```

### Lab 2 browser demo

完成 `demo_connection.py` 接線後，在同一 shell 執行 `python -m finops_agent demo`。預設只監聽 `127.0.0.1:8098`，User 與 Admin 連結在 console 顯示；用兩個分頁並排演示。每次啟動是獨立的 carol mock 帳號，限額 150、已用 102.67、剩餘 47.33。申請提高至 220 後先維持 pending 和原額度；人核准後才變成限額 220、已用 102.67、剩餘 117.33。

以 migration 剩餘 60 批次／USD 61.60、9/30 review 的理由銜接 Lab 1，但只提供 `get_my_costs`、`get_my_savings`、`request_budget_increase`。

若 SDK 認證或網路不可用，可用頁面上「直接提交 mock 申請（不經模型）」表單繼續演示人工核准；必須明說聊天尚未成功。頁面資料 refresh 不會消耗 model tokens。

### 方式 B：主辦方 BYOK

Foundry 的 `.env` 統一使用下面三個名稱，並明確選擇 `foundry-key`：

```env
FINOPS_MODEL_PROVIDER=foundry-key
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-api-key>
MODEL_NAME=<your-model-deployment-name>
```

`.env.example` 是設定說明，不會自動生效；複製為 `starter/.env` 後由 CLI 載入。Process environment 優先，不要同時留下不同 provider 的舊值。

Lab 2 選配的 identity 路線使用 `FINOPS_MODEL_PROVIDER=foundry-identity`、`AZURE_OPENAI_ENDPOINT`、`MODEL_NAME`；`AZURE_OPENAI_API_KEY` 留空即可。只有這種 provider 才會載入 Azure credential；Lab 1 與 Lab 2 的 Copilot 主線仍使用 `COPILOT_GITHUB_TOKEN` 和 `COPILOT_MODEL`，不需要 Azure。

## Lab 2 選配：Foundry Model 課前準備


| 方式 | 必要設定 | 身分／注意事項 |
| --- | --- | --- |
| `foundry-identity`（課程優先） | `AZURE_OPENAI_ENDPOINT` + `MODEL_NAME` | 本機以課前已登入、具權限的開發者身分取得 token；Hosted 才用 Managed Identity，不需 API key |
| `foundry-key`（主辦方備案） | `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` + `MODEL_NAME` | 模型填 deployment name，key 只存於當前 shell 或被忽略的本機 `.env` |

`AZURE_OPENAI_ENDPOINT` 接受 HTTPS 資源根網址（例如 `https://<resource>.openai.azure.com`）、Foundry project 根 endpoint（`https://<account>.services.ai.azure.com/api/projects/<project>`），或上述網址的 `/openai/v1/` base URL。不要填 `/responses`、`/chat/completions`、deployment 路徑或 Hosted Agent invoke endpoint，也不要在 URL 放 key 或 query string。

Hosted 部署時，`azure.yaml` 會把 azd 的 `AZURE_AI_MODEL_DEPLOYMENT_NAME` 對應到應用程式的 `MODEL_NAME`。若未另設 `AZURE_OPENAI_ENDPOINT`，harness 可使用平台注入的 `FOUNDRY_PROJECT_ENDPOINT`。
目前 Hosted manifest 預設模型為 `gpt-6-astra`，model version 以 `azure.yaml` 為準。
既有 azd environment 不會自動跟著 YAML 或本機 `.env` 換模型；
先確認實際 deployment，再依[Hosted 部署說明](hosted-deployment.md#這次部署什麼)同步綁定。

第一次設定請直接使用本節提供的變數名稱。若出現「舊 Foundry 設定遷移提醒」，再依[疑難排解](troubleshooting.md)更新既有設定；請勿混用新 endpoint 與舊 key。


## 安全與清理

課後退出 chat 與本機 host、撤銷活動 token，並移除 shell 認證。Azure 資源由主辦方依環境清單統一停用。座位、budget 和 audit 的 mock 狀態在程序結束即消失。
