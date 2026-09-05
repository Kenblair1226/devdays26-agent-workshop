# 環境準備與課前檢查

學員約 40 人，課程 90 分鐘。**課前完成安裝與認證**，不要把現場時間花在下載 SDK。課程的主線為本機 tools、本機 Copilot SDK harness、選配 Foundry 部署。

## 學員必要環境

| 項目 | Lab 1 | Lab 2 | Lab 3 |
| --- | --- | --- | --- |
| Git、VS Code、Python 3.13、repo | 必要 | 必要 | 必要 |
| Copilot SDK 與其 pinned runtime | 不需要模型呼叫 | 必要 | 必要 |
| 個人 Copilot token 或主辦方 BYOK | 不需要 | 模型問答時需要 | 視選定 model provider |
| Azure CLI、azd ≥1.27.1、Foundry extension | 不需要 | 不需要 | hands-on 才需要 |
| 預建 Foundry project、model、RBAC | 不需要 | 不需要 | 每人一套，或講師 demo |

Lab 2 是**在本機執行 harness**，不是 LLM 離線運行。使用 GitHub Copilot 模型時會消耗自己的 Copilot 額度；BYOK 的 inference 費用由 Azure/model provider 計費。這與範例中被分析的 GitHub billing data 是不同帳。

## 安裝（repository root）

先用 `python --version` 確認是 **3.13.x**。Windows 建議 PowerShell 7；執行政策不允許 activation 時，直接使用 venv 內的 `python.exe`，不要永久放寬系統政策。

PowerShell：

```powershell
python -m venv .\starter\.venv
& .\starter\.venv\Scripts\Activate.ps1
python -m pip install -r .\starter\requirements.txt
python -m copilot download-runtime
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
python -m finops_agent --data-dir .\data cost
```

bash：

```bash
python -m venv starter/.venv
source starter/.venv/bin/activate
python -m pip install -r starter/requirements.txt
python -m copilot download-runtime
export PYTHONPATH="$PWD/starter/src"
export FINOPS_BACKEND=mock
python -m finops_agent --data-dir data cost
```

SDK 固定為 `github-copilot-sdk==1.0.11`，由該 SDK 決定 runtime 版本。不要混用任意 PATH 上的 Copilot CLI。若跳過預下載，SDK 首次使用會下載 runtime，可能影響現場時間；**不需要獨立啟動 CLI server 或 Docker**。

預期 baseline：MTD net `4760` AI credits、`44.88` USD、snapshot `2026-09-03T23:59:59Z`。Starter 的 Lab 1/2 checks 在完成 TODO 前會失敗；`starter/tests` 是應該立即可過的 baseline。

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

### 方式 B：主辦方 BYOK

明確設定 `FINOPS_MODEL_PROVIDER=foundry-key`、`FOUNDRY_MODEL_URL`（OpenAI-compatible `/openai/v1/` endpoint）、`FOUNDRY_API_KEY`，以及 `COPILOT_MODEL`（**Azure deployment name**）。金鑰只放目前 shell 或本機被忽略的 `starter/.env`，不要放教材、Git、prompt 或群組聊天室。

`.env.example` 是設定說明，不會自動生效；複製為 `starter/.env` 後由 CLI 載入。Process environment 優先，不要同時留下不同 provider 的舊值。

Lab 3 的 Managed Identity 使用 `FINOPS_MODEL_PROVIDER=foundry-identity`、`FOUNDRY_PROJECT_ENDPOINT`、`AZURE_AI_MODEL_DEPLOYMENT_NAME`。只有這種 provider 才會載入 Azure credential；Lab 1/2 的 Copilot 路線不需要 Azure。

## 主辦方：40 套 Foundry 環境

Foundry hands-on 不是現場從零 provision。建議由 **1 位講師 + 3–4 位 TA** 支援，每位 TA 負責約 10–13 人；另準備一個講師 demo 與少數備用環境。

| 時點 | 主辦方完成事項 |
| --- | --- |
| T−7 天 | 確認地區、hosted/code deployment 支援、模型配額、使用成本上限；完成一套 golden environment |
| T−3 天 | 預建 40 套個人 project/environment，隔離登入與權限；確認 model deployment 名稱、Managed Identity 權限與模型呼叫 |
| T−1 天 | 每台/每人安裝 Python、依賴及 runtime；用實際課程 Wi-Fi 完成 Lab 2；對 40 套環境做小批量 deployment/invoke 彩排 |
| 開場前 | 講師 endpoint 與 logs 可用，備妥範例回應或錄影、checkpoint recovery、TA 分區表 |

只存在 Azure 資源還不夠：每人本機 `starter/.azure/` 必須已綁定正確的個人 azd environment。主辦方依 [Foundry Hosted Agent 部署指南](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent) 建立與綁定，`starter/azure.yaml` 是 code deployment 設定。不要把含 secrets 的 `.azure/` 複製給全班、提交到 Git，或讓全班共用講師的 admin identity。

每人課前需核對：project endpoint、部署模型名稱、azd environment、agent service `finops-agent`、Managed Identity model access、monitor 權限、code runtime `python_3_13`。如果需要初始化既有程式，依官方 `--src` / existing-project 流程操作；不要在現成 starter 上重複 `azd ai agent init` 產生第二個 agent service。

**配額與費用不是教材保證值。** YAML 的 CPU/memory 是每個執行實例設定；40 人並行、cold start、模型 RPM/TPM 與 runtime download egress 都需在活動地區實測。分四批啟動部署可降低同時重試壓力。不要因 429 讓全場無限 retry。

## Lab 3 可用條件與 fallback

第 63 分鐘，若多數學員已完成 Lab 2、個人環境已就緒，就進行 Lab 3。任何資源未開通或部署等候超過 5 分鐘，改用講師預部署端點；若講師雲端也不可用，播放課前錄影並對照 `main.py` / `azure.yaml`。要明確標示這是觀摩，不是現場已部署。

Cloud readiness 必須包含一次真正的 remote invocation；本機 `/readiness` 只代表 HTTP host 啟動，不能證明 Managed Identity、模型授權或完整 tool calling 已成功。

## 安全與清理

`FINOPS_BACKEND=mock` 是預設。學員不要設定 `GITHUB_ADMIN_TOKEN` 或 real-write flag；公司資料、個資、signed download URLs 和 keys 都不能放進 prompt / repo。全部 fixture 都是合成數字。

課後退出 chat 與本機 host、撤銷活動 token，並移除 shell 認證。Azure 資源由主辦方依環境清單統一停用；不要讓學員對共用 project 或 subscription 執行清除指令。座位、budget 和 audit 的 mock 狀態在程序結束即消失。
