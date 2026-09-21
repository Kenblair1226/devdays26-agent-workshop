# 實作工作坊：用 GitHub Copilot 與 Microsoft Foundry 建立 FinOps Agent

## 中文版

### 課程簡介

本工作坊以 **GitHub Copilot FinOps agent** 為情境，帶領學員完成 **3 個 Labs**，依核心成果與現場進度安排實作或示範：

> 本月 AI credits 成長異常。請找出主要原因，預估月底用量，提出兩個改善方案

1. **Lab 1**：GitHub Copilot Chat Agent 使用現成唯讀工具，從每日趨勢到 user/model，再按需查團隊／workflow；交付原因、月底估算與兩個方案的一頁決策摘要，選做網頁 dashboard
2. **Lab 2（local-only）**：只接上一個 Copilot SDK harness factory，使用者可詢問個人花費與節省建議、申請提高限額，管理者從另一個頁面核准；選配讓同一個 harness 改用 Foundry Model 重跑
3. **Lab 3（optional）**：將同一個 Agent direct-code deploy 到 Foundry Hosted Agent；hosting 未就緒時觀摩講師 demo

### 課程重點

- 了解 `starter/` 如何作為真正的 hands-on learner path
- 先讓觀眾選值得追查的團隊，再用工作量、不同成功成果與每成果成本檢驗假設；高用量不等於浪費，Unallocated 保留在總額但不是主角
- 固定快照為 `2026-09-22T23:59:59Z`，MTD 涵蓋 2026-09-01～2026-09-22：**34,906.67 credits／USD 329.12**。全部預先模擬，不是實測或真實帳務，也不支持季節性推論
- 在 VS Code 開啟 repo 根目錄，以 Agent 模式使用本專案的 [`/finops-investigation`](.github/skills/finops-investigation/SKILL.md)；工具目錄與長指令由 skill 提供，不先附整份答案。無須全域安裝；skill 不是 IDE 權限沙箱，也不啟用 Python SDK skills
- `trend` 的 2026-08-01～2026-08-22 比較資料是獨立合成 fixture，普通 billing `previous_month` 不支援；同為 22 日的兩期成長 62.18% credits／74.83% USD，不是完整月帳單
- 調查後才讀 `options`，從修正重複觸發、簡單任務換模型、暫時提高預算中**選兩個**；比較 owner、品質 gate、同期間效果與不選理由，headroom 不是節省。`forecast 600` 的 47,600 credits／USD 448.80 是歷史 run-rate，不是保證
- 完成摘要後才匯出調查 evidence，選做由 Agent 建立單一 HTML，練習「圖表也要對得回證據」
- 練習 human-in-the-loop mock governance boundary
- 了解 official Foundry direct-code shape：`azure.yaml` + `main.py`，組合 `InvocationAgentServerHost` 與 `ResponsesAgentServerHost`
- Foundry 擴充只加入模型來源切換，不增加 Toolbox 或其他服務；工具與核准流程維持不變
- 知道 `solution/` 是答案與 recovery，不是主要操作路徑

### 重要前提

- 語言：**繁體中文**，保留 English technical terms
- Python：**3.13**
- Lab 2 在 `starter/` 接線；Lab 1 的摘要與選做作品放在 `workshop-output/`。`solution/` 用來比對，`scripts/checkpoint.py` 提供有備份的 recovery
- 建議課前先在 `starter/.venv` 安裝 `starter/requirements.txt`，並預先執行 `python -m copilot download-runtime`
- Lab 1 的現成工具無需認證；Copilot Chat 分析需在 VS Code 登入有 Copilot 權限的 GitHub 帳號，不需 SDK token 或 Azure 資源
- Lab 1 完成決策後用 `brief --include-investigation` 匯出 evidence；一般 `brief` 不預載團隊脈絡，輸出已存在就換新名稱
- 選做 [`/finops-dashboard`](.github/skills/finops-dashboard/SKILL.md) 沿用 Copilot 登入與 Clawpilot 樣式；檢視後只建立 `workshop-output/finops-dashboard.html`，以 File API 載入 evidence，不新增依賴、CDN、網路、server 或管理操作
- Lab 2 的頁面與 mock 核准可在本機執行；**SDK 聊天需要 `COPILOT_GITHUB_TOKEN` 或 organizer BYOK**，不需正式 org 權限或 SSO
- Lab 2 只有 `get_my_costs`、`get_my_savings`、`request_budget_increase` 三個個人工具，不提供組織 roster／workflow 或模型核准。用 carol 的 migration 理由演練 150／102.67／47.33 → 人核准後 220／102.67／117.33；+70 headroom 不是成本下降，mock expiry 不代表自動回復
- Lab 2 的 model switch 優先使用主辦單位預配置的 Foundry model；Lab 3 Hosted Agent 使用 Managed Identity，且 `starter/azure.yaml` 需要 **azd >= 1.27.1**
- 不要使用 admin / billing token

### 快速連結

- [README.md](README.md)
- [docs/environment-prep.md](docs/environment-prep.md)
- [docs/student-lab.md](docs/student-lab.md)
- [docs/instructor-guide.md](docs/instructor-guide.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)

### 注意事項

- 請自備筆電、充電器與穩定網路
- 請確認可使用 GitHub Copilot
- 若主辦單位未預先快取 Copilot runtime，第一次 `ask` 可能自動下載；建議在課前完成
- 請勿貼上公司機密、個資、正式環境資料、API Key 或 admin token
- Lab 1 與 Lab 2 的完成率優先於 Lab 3 infra 排障

---

# Hands-on Workshop: Build a FinOps Agent with GitHub Copilot and Microsoft Foundry

## English Version

### Overview

This workshop has exactly three labs. Progress through the core outcomes, with optional work guided by learner readiness and available environments:

> This month's AI credits have grown unexpectedly. Find the main causes, estimate month-end usage, and propose two improvements.

1. **Lab 1**: Copilot Chat Agent uses ready-made read-only tools, moving from daily trends to user/model distribution and on-demand team/workflow evidence; produce a one-page cause, forecast, and two-option decision brief, with an optional local dashboard
2. **Lab 2 (local-only)**: connect one Copilot SDK harness factory; a user asks about spending and savings, requests a higher limit, and an administrator approves on a separate page; optionally switch the same harness to a Foundry model and repeat the flow
3. **Lab 3 (optional)**: direct-code deploy the same agent as a Foundry Hosted Agent, or watch the instructor demo when hosting is unavailable

### Highlights

- `starter/` is the learner path
- `solution/` is the answer / recovery path
- Let the audience choose which team to investigate, then check workload, distinct successful outcomes, and cost per outcome before calling high usage waste. Preserve Unallocated in accounting totals without making it the main plot; no mandatory seat removal
- The fixed snapshot is `2026-09-22T23:59:59Z`, with MTD covering September 1–22: **34,906.67 credits / USD 329.12**. All data is pre-simulated, not measured usage or real account data, and does not establish seasonality
- Open the repository root in VS Code and use the project-local [`/finops-investigation`](.github/skills/finops-investigation/SKILL.md) in Agent mode. The skill supplies the detailed instructions and tool catalog; do not attach the answer package upfront. No global installation is needed. Skills are not permission sandboxes and do not enable skills in the Python SDK runtime
- The August 1–22 matched comparison is a separate fictional fixture; ordinary billing `previous_month` remains unsupported. Both periods cover 22 calendar days; growth is 62.18% in credits and 74.83% in USD, not a full-month invoice
- After investigating workload and outcomes, compare three options: deduplicate triggers, switch only eligible simple tasks to a smaller model, or temporarily increase a user's budget. Choose two with an owner, quality gate, measurable follow-up, and one rejected alternative. Budget headroom is not savings; 47,600 credits / USD 448.80 is a historical run-rate forecast, not a guarantee
- Only after the decision, export with `brief --include-investigation`; ordinary `brief` does not eagerly load business context. Choose a new filename if the output already exists
- Optionally use [`/finops-dashboard`](.github/skills/finops-dashboard/SKILL.md) for a single Clawpilot-themed HTML file, reviewed before opening, that loads evidence through File API. No source/`.env` changes, dependencies, server, CDN, network calls, management actions, or automatic execution/upload. The decision brief remains Checkpoint 1
- Pre-event setup should install `starter/requirements.txt` into `starter/.venv` and pre-cache `python -m copilot download-runtime`
- Lab 1 analysis uses signed-in VS Code Copilot Chat; Lab 2 uses the local SDK harness with Copilot auth or organizer BYOK. Neither requires Azure hosting
- Lab 2 exposes only `get_my_costs`, `get_my_savings`, and `request_budget_increase`, not organization workflow data or approval. Use the migration plan to rehearse 150/102.67/47.33 → human approval → 220/102.67/117.33. The extra USD 70 is headroom, not savings; mock expiry metadata is not an automatic reversion timer
- Optional Hosted deployment uses `starter/azure.yaml`, `starter/main.py`, and a combined Invocations/Responses host, and requires **azd >= 1.27.1**; the model-only step runs in the local demo
- The only new Foundry integration is the model provider; Toolbox and additional services are out of scope. Using a Foundry model locally does not require agent hosting or azd

### Prerequisites

- Python **3.13**
- GitHub account with GitHub Copilot access
- Workshop repo with `starter/`, `solution/`, and `data/`
- Copilot auth or organizer BYOK for the Lab 2 SDK chat; user/admin pages use local mock roles
- A preprovisioned Foundry model for the optional Lab 2 switch and a hosting environment for Lab 3 hands-on

### Links

- [README.md](README.md)
- [docs/environment-prep.md](docs/environment-prep.md)
- [docs/student-lab.md](docs/student-lab.md)
- [docs/instructor-guide.md](docs/instructor-guide.md)

### Important Information

- Do not use admin or billing tokens
- Do not upload confidential, personal, or production data
- Learners connect the Lab 2 factory in `starter/`; `solution/` is the reference and `scripts/checkpoint.py` restores checkpoints with backups. Lab 1 analysis and optional dashboard files stay in `workshop-output/`, outside source checkpoints
- Lab 3 may switch to instructor demo if Hosted Agent deployment is slow or resources are unavailable
