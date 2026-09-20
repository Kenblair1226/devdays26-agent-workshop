# 環境準備與課前檢查

學員約 40 人。**課前完成安裝與認證**，讓現場可以專心實作。課程的主線為現成工具 + Copilot Chat Agent 逐步調查、本機 Copilot SDK harness、Foundry Model 切換及原有的選配部署。不加入 Toolbox、檢索或新的觀測服務。

## 學員必要環境

| 項目 | Lab 1 | Lab 2 | Lab 3 |
| --- | --- | --- | --- |
| Git、VS Code、Python 3.13、repo | 必要 | 必要 | 必要 |
| VS Code Copilot Chat 登入／使用權限 | Agent 唯讀 terminal 調查；Ask 作逐次貼結果的備案，選做 dashboard 建檔 | 可作開發輔助 | 不影響 hosting |
| Copilot SDK 與其 pinned runtime | 報表工具不需要 | 必要 | 必要 |
| 瀏覽器與可用的 localhost port | 選做 dashboard 用瀏覽器開本機檔案，不佔 port | 8098，User/Admin 兩分頁 | 依主辦方環境 |
| 個人 Copilot token 或主辦方 BYOK | 不需要 | 模型問答時需要 | 視選定 model provider |
| Azure CLI 登入或模型 key | 不需要 | Copilot 主線不需要 | Foundry 模型呼叫需其一 |
| azd ≥1.27.1、Foundry extension、hosting 環境 | 不需要 | 不需要 | 選配 Hosted 部署才需要 |
| 預建 Foundry project、model、RBAC | 不需要 | Copilot 主線不需要 | 個人配發的環境，或講師 demo |

Lab 1 的現成 deterministic CLI（包含 `trend`、`roster`、`workflows`、`options`）只讀 mock fixtures，不載入 SDK／Azure client；設好 `PYTHONPATH` 後連 `python -S -m finops_agent --data-dir data trend` 也可執行。Copilot Chat 仍需既有 GitHub 登入，但不需 SDK token。完整 `brief` 留到分析／選擇後才匯出。Lab 2 是**在本機執行 harness**，不是 LLM 離線運行。使用 GitHub Copilot 模型時會消耗自己的 Copilot 額度；BYOK 的 inference 費用由 Azure/model provider 計費。這與範例中被分析的 GitHub billing data 是不同帳。

## 安裝（repository root）

`.venv` 不會隨 repo 提供，第一次 clone 後要在自己的電腦建立。以下從 repo 根目錄執行，先確認是 **Python 3.13.x**；版本不對或建立失敗時先修正，不要直接執行啟用指令。

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

SDK 固定為 `github-copilot-sdk==1.0.11`，由該 SDK 決定 runtime 版本。不要混用任意 PATH 上的 Copilot CLI。若跳過預下載，SDK 首次使用會下載 runtime，可能中斷操作節奏；**不需要獨立啟動 CLI server 或 Docker**。

預期輸出：MTD net `34906.67` AI credits、`329.12` USD、snapshot `2026-09-22T23:59:59Z`，期間為 **2026-09-01～2026-09-22**。全部預先模擬，不是實測或真實帳單。`starter/tests` 與 `starter/checks/test_lab1.py` 應開箱即通過；只有 Lab 2 checks 在完成 SDK TODO 前會失敗。

## Lab 1 Copilot Chat 準備

在 VS Code 開啟 **repo 根目錄**（不是只開 `starter/`），登入 Copilot 並選 **Agent 模式**。依 [學員手冊](student-lab.md) 使用本專案的 [調查 skill `/finops-investigation`](../.github/skills/finops-investigation/SKILL.md)，由 skill 提供工具目錄與逐步調查指令；不先附完整 evidence、教師答案或跑 `options`。

Agent 使用前面已初始化的 terminal；新 terminal 只需啟用既有 venv、重設 `PYTHONPATH`、`FINOPS_BACKEND=mock` 與 `FINOPS_ALLOW_REAL_WRITES=false`，不重建或安裝。Skills 只供 VS Code IDE，不啟用 Python SDK skills，也不是權限沙箱；仍須檢視命令，不讀憑證、不改 source／`.env` 或呼叫外部管理 API。

找不到 skill 時，在 Chat 輸入 `/skills` 開啟 Configure Skills，確認 `chat.useAgentSkills` 已啟用（目前預設 true）；也可直接輸入 `/finops-investigation` 或 `/finops-dashboard`。仍不可用就附上對應 `SKILL.md`，請 Agent 手動遵循；無須全域安裝、個人 Skill Manager 或額外 extension。詳見 [疑難排解](troubleshooting.md)。

`trend` 使用獨立 **2026-08-01～2026-08-22** 比較期，普通 billing `previous_month` 不支援。缺案例檔請找 TA，不補零或捏造資料。若 Agent／terminal tools 不可用，由人執行下一個唯讀命令、逐次貼給 Ask；Chat 也不可用就與鄰座共看，不交換帳密。

### 選做 dashboard 的準備

完成決策摘要後，用 `python -m finops_agent --data-dir data brief --include-investigation --output workshop-output/lab1-evidence.json` 匯出；已存在就換新名稱。一般 `brief` 不預載調查脈絡。接著輸入 `/finops-dashboard 用 workshop-output/lab1-evidence.json 製作本機 dashboard`；[dashboard skill](../.github/skills/finops-dashboard/SKILL.md) 提供單一 HTML、資料驗證與 Clawpilot 樣式規則。

檢視 edits 後才接受、手動開啟，以 File API 選取 evidence；不改 source／`.env`，不新增依賴、CDN、網路、server 或管理操作。瀏覽器不需模型憑證；若 `file://` 載入失敗，修正選檔方式而不是開服務。選做不影響 Checkpoint 1，未完成仍可進 Lab 2。

## Lab 2 模型認證

### 方式 A：個人 GitHub Copilot（本機主線）

依 [SDK authentication](https://docs.github.com/en/copilot/how-tos/copilot-sdk/auth/authenticate) 建立活動用 fine-grained PAT，授予 **Account permissions → Copilot Requests → Read-only**，並確認帳號及組織政策允許 Copilot SDK 使用。這不是 org billing/admin token。

用隱藏輸入避免把 token 留在 shell history：

```powershell
$env:FINOPS_MODEL_PROVIDER = "copilot"
$env:COPILOT_GITHUB_TOKEN = Read-Host "Workshop Copilot token" -MaskInput
$env:COPILOT_MODEL = "gpt-5"
python -m finops_agent ask "目前本月的範例費用是多少？"
```

```bash
export FINOPS_MODEL_PROVIDER=copilot
read -rsp "Workshop Copilot token: " COPILOT_GITHUB_TOKEN; printf '\n'
export COPILOT_GITHUB_TOKEN
export COPILOT_MODEL=gpt-5
python -m finops_agent ask "目前本月的範例費用是多少？"
```

模型名稱需是該帳號可用的模型。Token 到期、模型政策或額度不足不是缺少 Foundry；由 TA 協助確認，必要時兩人共用一台已登入的機器操作，**不交換 token**。

### Lab 2 browser demo

完成 `demo_connection.py` 接線後，在同一 shell 執行 `python -m finops_agent demo`。預設只監聽 `127.0.0.1:8098`，User 與 Admin 連結在 console 顯示；用兩個分頁並排演示。每次啟動是獨立的 carol mock 帳號，限額 150、已用 102.67、剩餘 47.33。申請提高至 220 後先維持 pending 和原額度；人核准後才變成限額 220、已用 102.67、剩餘 117.33。

以 migration 剩餘 60 批次／USD 61.60、9/30 review 的理由銜接 Lab 1，但只提供 `get_my_costs`、`get_my_savings`、`request_budget_increase`。組織調查工具不加入此 allowlist，模型沒有 approve。USD 70 headroom 不是節省；`expires_at` 是 mock metadata，不是自動回復服務。

不用 Node、React build、Docker 或正式登入。已在 Python requirements 內列出 Starlette / Hypercorn。不要用公開 tunnel 或 `0.0.0.0` 將 demo 對外開放；它的角色 capability 只是單機教學邊界，持有 admin link 就代表管理者。重啟會恢復初始資料，舊連結失效。

若 SDK 認證或網路不可用，可用頁面上「直接提交 mock 申請（不經模型）」表單繼續演示人工核准；必須明說聊天尚未成功。頁面資料 refresh 不會消耗 model tokens。

### 方式 B：主辦方 BYOK

Foundry 的 `.env` 統一使用下面三個名稱，並明確選擇 `foundry-key`：

```env
FINOPS_MODEL_PROVIDER=foundry-key
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-api-key>
MODEL_NAME=<your-model-deployment-name>
```

`MODEL_NAME` 是 **Azure deployment name**，不是 GitHub 模型 ID。Endpoint 可填資源根網址，或包含 `/openai/v1/` 的完整 base URL，程式會補齊路徑且不會重複加上。金鑰只放目前 shell 或本機被忽略的 `starter/.env`，不要放教材、Git、prompt 或群組聊天室。

`.env.example` 是設定說明，不會自動生效；複製為 `starter/.env` 後由 CLI 載入。Process environment 優先，不要同時留下不同 provider 的舊值。

Lab 3 的 identity 路線使用 `FINOPS_MODEL_PROVIDER=foundry-identity`、`AZURE_OPENAI_ENDPOINT`、`MODEL_NAME`；`AZURE_OPENAI_API_KEY` 留空即可。只有這種 provider 才會載入 Azure credential；Lab 1/2 的 Copilot 路線仍使用 `COPILOT_GITHUB_TOKEN` 和 `COPILOT_MODEL`，不需要 Azure。

## Lab 3 Foundry Model 課前準備

只使用主辦方**已部署、已完成 tool-calling 彩排**的模型，不現場選 region、申請配額或新增模型。此 harness 使用 OpenAI-compatible Responses API，並非 Foundry catalog 裡每一個模型都一定相容。模型名稱必須填 Azure 的 deployment name；同一個模型來源切換不需要改 UI 或工具。

| 方式 | 必要設定 | 身分／注意事項 |
| --- | --- | --- |
| `foundry-identity`（課程優先） | `AZURE_OPENAI_ENDPOINT` + `MODEL_NAME` | 本機以課前已登入、具權限的開發者身分取得 token；Hosted 才用 Managed Identity，不需 API key |
| `foundry-key`（主辦方備案） | `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` + `MODEL_NAME` | 模型填 deployment name，key 只存於當前 shell 或被忽略的本機 `.env` |

`AZURE_OPENAI_ENDPOINT` 接受 HTTPS 資源根網址（例如 `https://<resource>.openai.azure.com`）、Foundry project 根 endpoint（`https://<account>.services.ai.azure.com/api/projects/<project>`），或上述網址的 `/openai/v1/` base URL。不要填 `/responses`、`/chat/completions`、deployment 路徑或 Hosted Agent invoke endpoint，也不要在 URL 放 key 或 query string。

Hosted 部署時，`azure.yaml` 會把 azd 的 `AZURE_AI_MODEL_DEPLOYMENT_NAME` 對應到應用程式的 `MODEL_NAME`；這個 azd 來源變數維持原名。若未另設 `AZURE_OPENAI_ENDPOINT`，harness 仍可使用平台注入的 `FOUNDRY_PROJECT_ENDPOINT`，不用為了改 `.env` 命名而重建環境。

舊 `.env` 的 `FOUNDRY_MODEL_URL`／`FOUNDRY_API_KEY`／`COPILOT_MODEL` 完整組合仍可相容讀取，並顯示遷移提醒；新 key 設定優先，請整組改用新名稱，不要混用新 endpoint 與舊 key。Identity 路線保留平台 endpoint／舊 deployment 變數的相容來源。範例與課程命令一律使用新名稱。

使用 identity 的學員需課前自行登入 Azure CLI 等受支援的開發者憑證來源，由主辦方核對 inference 權限；**有 portal 閱讀權限不代表能呼叫模型**。課程程式不會替學員執行登入或建立 role assignment。若政策要求禁用 keys，就不啟用 key 備案。

切換前用 `Ctrl+C` 停止 demo，依學員手冊設定 provider 後重新啟動。Mock budgets／requests 與角色連結會重設，這不是把不同模型的對話或核准狀態接續使用。不要一邊跑 server 一邊改 shell 變數，既有 process 不會自動取得新值。

若使用 key 備案，在主辦方提供 endpoint 與 deployment name 後，PowerShell 以 `Read-Host -MaskInput` 讀入 `AZURE_OPENAI_API_KEY`；bash 以 `read -rsp` 讀入後 export。不要把真實 key 寫進示範命令、截圖、聊天室或 Git。模型 key 不是 GitHub admin token。

課前需用**實際認證的 SDK 聊天**跑完查費用、節省建議、申請及 admin approve。只跑 mock tests、看到卡片或 `/readiness` 200，不代表 Foundry 模型與權限可用。

使用 Foundry Model 的 inference 費用與 Copilot 額度是兩筆帳，GitHub budget 不限制 Azure 費用。限制課堂重試／並行呼叫，依模型 deployment 的實際 RPM／TPM 準備 40 人容量；不保證切換後一定更便宜。

## 主辦方：40 套 Foundry 環境

Foundry hands-on 不是現場從零 provision。建議由 **1 位講師 + 3–4 位 TA** 支援，每位 TA 負責約 10–13 人；另準備一個講師 demo 與少數備用環境。

| 準備階段 | 主辦方完成事項 |
| --- | --- |
| 環境設計 | 確認地區、hosted/code deployment 支援、模型配額、使用成本上限；完成一套 golden environment |
| 個人環境建置 | 預建 40 套個人 project/environment，隔離登入與權限；確認 model deployment 名稱、Managed Identity 權限與模型呼叫 |
| 功能彩排 | 每台/每人安裝 Python、依賴及 runtime；確認 Lab 1 Agent terminal／Ask fallback 的逐步證據、決策後匯出、Lab 2 User/Admin、Foundry Model 切換及回復；若示範選做 dashboard，另核對本機選檔與加總；若要部署，另做小批量 deployment/invoke 彩排 |
| 開場檢查 | 講師 endpoint 與 logs 可用，備妥範例回應或錄影、checkpoint recovery、TA 分區表 |

只存在 Azure 資源還不夠：每人本機 `starter/.azure/` 必須已綁定正確的個人 azd environment。主辦方依 [Foundry Hosted Agent 部署指南](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent) 建立與綁定，`starter/azure.yaml` 是 code deployment 設定。不要把含 secrets 的 `.azure/` 複製給全班、提交到 Git，或讓全班共用講師的 admin identity。

每人課前需核對：project endpoint、部署模型名稱、azd environment、agent service `finops-agent`、Managed Identity model access、monitor 權限、code runtime `python_3_13`。如果需要初始化既有程式，依官方 `--src` / existing-project 流程操作；不要在現成 starter 上重複 `azd ai agent init` 產生第二個 agent service。

**配額與費用不是教材保證值。** YAML 的 CPU/memory 是每個執行實例設定；40 人並行、cold start、模型 RPM/TPM 與 runtime download egress 都需在活動地區實測。分四批啟動部署可降低同時重試壓力。不要因 429 讓全場無限 retry。

## Lab 3 可用條件與 fallback

進入 Lab 3 前，先確認 Lab 2 核心成果、模型與 inference 權限，再做 Foundry Model 切換；只有 hosting 也預備好才進入部署。模型或權限不可用時看講師模型 demo，或明確切回 Copilot；hosting 未開通、部署受阻或持續等待時，改用講師預部署端點。若講師雲端也不可用，播放課前錄影。模型呼叫、hosting 部署與觀摩要分別標示，不互相代替。

Cloud readiness 必須包含一次真正的 remote invocation；本機 `/readiness` 只代表 HTTP host 啟動，不能證明 Managed Identity、模型授權或完整 tool calling 已成功。

## 安全與清理

`FINOPS_BACKEND=mock` 是預設。學員不要設定 `GITHUB_ADMIN_TOKEN` 或 real-write flag；公司資料、個資、signed download URLs 和 keys 都不能放進 prompt / repo。全部 fixture 都是合成數字。

課後退出 chat 與本機 host、撤銷活動 token，並移除 shell 認證。Azure 資源由主辦方依環境清單統一停用；不要讓學員對共用 project 或 subscription 執行清除指令。座位、budget 和 audit 的 mock 狀態在程序結束即消失。
