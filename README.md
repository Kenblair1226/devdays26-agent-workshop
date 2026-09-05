# Copilot FinOps Agent Workshop

以 **Python 3.13 + GitHub Copilot SDK + Microsoft Foundry**，在 90 分鐘內帶約 40 位學員完成可查詢費用、分析部門用量、提出節省建議及管理 seat/budget 計畫的 Agent。

| Lab | Hands-on | 執行位置 |
| --- | --- | --- |
| 1 | 完成 FinOps 部門 aggregation、費用與預算工具 | 本機，synthetic data，無認證需求 |
| 2 | 整合 SDK tools / instructions、自然語言問答、人工確認 | 本機 harness，Copilot 或 BYOK model |
| 3 | Direct-code deploy、remote invoke、觀測 | Foundry；時間或資源不足改講師 demo |

**學員入口：[環境準備](docs/environment-prep.md) → [學員手冊](docs/student-lab.md)。**
講師請先讀 [90 分鐘 runbook](docs/instructor-guide.md)，並參考 [架構](docs/architecture.md) 與 [疑難排解](docs/troubleshooting.md)。[intro.md](intro.md) 保留中英文活動簡介。

## Repository

- `starter/`：學員實作；只留下 Lab 1 aggregation、Lab 2 instructions / registrations 的 TODO。
- `solution/`：完整參考實作與 tests，和 starter 使用相同介面。
- `data/`：合成、已正規化的教學報表；service folders 內附同樣資料供部署。
- `scripts/checkpoint.py`：先備份學員編輯，再還原指定 checkpoint。

完成課前安裝後，在 repository root：

```powershell
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
python -m finops_agent cost
```

bash：`PYTHONPATH=starter/src FINOPS_BACKEND=mock python -m finops_agent cost`。
基準答案為 MTD **4,760 net AI credits / USD 44.88**；完成 Lab 1 後，部門第一名是 **AI Lab，2,400 credits**。

## 安全與邊界

預設 `FINOPS_BACKEND=mock`。Lab 2 `ask` / `chat` 會呼叫模型，因此需要 Copilot 或 BYOK 認證；Lab 1 不需 Azure。SDK 自管 runtime，沒有額外 headless service 或自訂 Dockerfile。Lab 3 的 hosted 範例固定使用 mock、每次 invocation 獨立。

真實 GitHub 操作僅限 instructor CLI，寫入還需 write flag、有效的計畫核准及明確的人確認。**不提交 token、公司資料、session history 或 audit logs。** Credits 不是原始 tokens；合成資料的價格不是正式 invoice。

Foundry 的個人環境、Managed Identity 與 remote invocation 需由主辦方課前準備；教材與本機演練不能替代活動環境的實際開通。
