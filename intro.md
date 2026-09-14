# 實作工作坊：用 GitHub Copilot 與 Microsoft Foundry 建立 FinOps Agent

## 中文版

### 課程簡介

本工作坊以 **GitHub Copilot FinOps agent** 為情境，帶領學員在 90 分鐘內完成 **剛好 3 個 Labs**：

1. **Lab 1（免寫程式）**：使用現成 FinOps tools 產生合成資料分析包，透過 GitHub Copilot Chat 調查成本、seat 與 budget，交付一頁決策摘要
2. **Lab 2（local-only）**：只接上一個 Copilot SDK harness factory，使用者可詢問個人花費與節省建議、申請提高限額，管理者從另一個頁面核准
3. **Lab 3（optional）**：讓同一個 Copilot SDK harness 改用 Foundry Model，重跑費用查詢與核准情境；環境與時間允許時再 direct-code deploy 到 Foundry Agent Service，否則由講師 demo

### 課程重點

- 了解 `starter/` 如何作為真正的 hands-on learner path
- 透過成本總覽、seat 使用檢視與預算分析情境，用合成資料比較節省方案
- 練習 human-in-the-loop mock governance boundary
- 了解 official Foundry direct-code shape：`azure.yaml` + `main.py` + `InvocationAgentServerHost`
- Foundry 擴充只加入模型來源切換，不增加 Toolbox 或其他服務；工具與核准流程維持不變
- 知道 `solution/` 是答案與 recovery，不是主要操作路徑

### 重要前提

- 語言：**繁體中文**，保留 English technical terms
- Python：**3.13**
- 學員在 `starter/` 實作；`solution/` 用來比對，`scripts/checkpoint.py` 提供有備份的分階段 recovery
- 建議課前先在 `starter/.venv` 安裝 `starter/requirements.txt`，並預先執行 `python -m copilot download-runtime`
- Lab 1 的現成工具無需認證；Copilot Chat 分析需在 VS Code 登入有 Copilot 權限的 GitHub 帳號，不需 SDK token 或 Azure 資源
- Lab 2 的頁面與 mock 核准可在本機執行；**SDK 聊天需要 `COPILOT_GITHUB_TOKEN` 或 organizer BYOK**，不需正式 org 權限或 SSO
- Lab 3 優先使用主辦單位預配置的 Foundry model 與 Managed Identity，且 `starter/azure.yaml` 需要 **azd >= 1.27.1**
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

This 90-minute workshop has exactly three labs:

1. **Lab 1 (no coding)**: use ready-made local tools and GitHub Copilot Chat to investigate synthetic cost, seat, and budget data and produce a one-page decision brief
2. **Lab 2 (local-only)**: connect one Copilot SDK harness factory; a user asks about spending and savings, requests a higher limit, and an administrator approves on a separate page
3. **Lab 3 (optional)**: switch the same Copilot SDK harness to a Foundry model and repeat the cost/approval flow; proceed with direct-code hosting when prepared, or watch the instructor demo

### Highlights

- `starter/` is the learner path
- `solution/` is the answer / recovery path
- Explore cost visibility, seat review, attribution, budgets, and conditional savings estimates with synthetic data; no additional platform installation required
- Pre-event setup should install `starter/requirements.txt` into `starter/.venv` and pre-cache `python -m copilot download-runtime`
- Lab 1 analysis uses signed-in VS Code Copilot Chat; Lab 2 uses the local SDK harness with Copilot auth or organizer BYOK. Neither requires Azure hosting
- Optional Hosted deployment uses `starter/azure.yaml`, `starter/main.py`, and `InvocationAgentServerHost`, and requires **azd >= 1.27.1**; the model-only step runs in the local demo
- The only new Foundry integration is the model provider; Toolbox and additional services are out of scope. Using a Foundry model locally does not require agent hosting or azd

### Prerequisites

- Python **3.13**
- GitHub account with GitHub Copilot access
- Workshop repo with `starter/`, `solution/`, and `data/`
- Copilot auth or organizer BYOK for the Lab 2 SDK chat; user/admin pages use local mock roles
- A preprovisioned Foundry environment for Lab 3 hands-on

### Links

- [README.md](README.md)
- [docs/environment-prep.md](docs/environment-prep.md)
- [docs/student-lab.md](docs/student-lab.md)
- [docs/instructor-guide.md](docs/instructor-guide.md)

### Important Information

- Do not use admin or billing tokens
- Do not upload confidential, personal, or production data
- Learners edit `starter/`; `solution/` is the reference and `scripts/checkpoint.py` restores checkpoints with backups
- Lab 3 may switch to instructor demo if deployment is slow or resources are unavailable
