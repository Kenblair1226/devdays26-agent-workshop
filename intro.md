# 實作工作坊：用 GitHub Copilot 與 Microsoft Foundry 建立 FinOps Agent

## 中文版

### 課程簡介

本工作坊以 **GitHub Copilot FinOps agent** 為情境，帶領學員在 90 分鐘內完成 **剛好 3 個 Labs**：

1. **Lab 1（local-only）**：編輯 `starter/src/finops_agent/analytics.py` 的 `TODO(Lab 1)`，完成 department aggregation 與 baseline analytics
2. **Lab 2（local-only）**：編輯 `starter/src/finops_agent/instructions.py` 與 `starter/src/finops_agent/sdk_tools.py`，完成 Copilot SDK tool surface 與 mock governance flow
3. **Lab 3（optional）**：從 `starter/` direct-code deploy 到 Microsoft Foundry Agent Service，進行 remote invoke 與 monitor；若環境不可用、部署過慢或時間不足，由講師 demo predeployed endpoint

### 課程重點

- 了解 `starter/` 如何作為真正的 hands-on learner path
- 使用 `data/` synthetic data 完成 FinOps analytics
- 練習 human-in-the-loop mock governance boundary
- 了解 official Foundry direct-code shape：`azure.yaml` + `main.py` + `InvocationAgentServerHost`
- 知道 `solution/` 是答案與 recovery，不是主要操作路徑

### 重要前提

- 語言：**繁體中文**，保留 English technical terms
- Python：**3.13**
- 學員在 `starter/` 實作；`solution/` 用來比對，`scripts/checkpoint.py` 提供有備份的分階段 recovery
- 建議課前先在 `starter/.venv` 安裝 `starter/requirements.txt`，並預先執行 `python -m copilot download-runtime`
- Lab 2 的 deterministic checkpoint 與 tool wiring 是 local-only，但 **`ask` 需要 `COPILOT_GITHUB_TOKEN` 或 organizer BYOK**
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

1. **Lab 1 (local-only)**: implement the `TODO(Lab 1)` in `starter/src/finops_agent/analytics.py`
2. **Lab 2 (local-only)**: replace the TODO rules in `starter/src/finops_agent/instructions.py` and register the missing SDK tools in `starter/src/finops_agent/sdk_tools.py`
3. **Lab 3 (optional)**: direct-code deploy the hosted agent from `starter/` to Microsoft Foundry Agent Service, then remotely invoke and monitor it; if resources or time are limited, the instructor demos a predeployed endpoint

### Highlights

- `starter/` is the learner path
- `solution/` is the answer / recovery path
- Pre-event setup should install `starter/requirements.txt` into `starter/.venv` and pre-cache `python -m copilot download-runtime`
- Labs 1 and 2 stay local, but the Lab 2 `ask` step requires Copilot auth or organizer BYOK
- Lab 3 uses the official direct-code Foundry shape with `starter/azure.yaml`, `starter/main.py`, and `InvocationAgentServerHost`, and requires **azd >= 1.27.1**

### Prerequisites

- Python **3.13**
- GitHub account with GitHub Copilot access
- Workshop repo with `starter/`, `solution/`, and `data/`
- Copilot auth or organizer BYOK for the Lab 2 `ask` step
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
