# Copilot FinOps Agent Workshop

以 **Python 3.13 + GitHub Copilot SDK + Microsoft Foundry**，帶約 40 位學員透過三個 Labs，完成可查詢費用、分析部門用量、提出節省建議及管理 seat/budget 計畫的 Agent。

| Lab | Hands-on | 執行位置 |
| --- | --- | --- |
| 1 | 用現成工具 + Copilot Chat 調查成本、seats、budgets，交付決策摘要；選做網頁 dashboard | 本機 mock 資料；Copilot Chat 使用既有 GitHub 登入 |
| 2 | 一次 harness 接線：查費用／節省建議 → 申請提高限額 → 管理者 approve | 本機使用者／管理者頁面，Copilot 或 BYOK model |
| 3 | 同一個 harness 換成 Foundry Model，再選配 direct-code deploy | 預建模型；依環境與學員進度選擇實作或講師 demo |

**學員入口：[環境準備](docs/environment-prep.md) → [學員手冊](docs/student-lab.md)。**
講師請先讀 [講師指南](docs/instructor-guide.md)，並參考 [架構](docs/architecture.md) 與 [疑難排解](docs/troubleshooting.md)。[intro.md](intro.md) 保留中英文活動簡介。

## Repository

- `starter/`：Lab 1 tools 全數可用；Lab 2 只在 `demo_connection.py` 留一個 harness factory TODO。
- `solution/`：完整參考實作與 tests，和 starter 使用相同介面。
- `data/`：合成、已正規化的教學報表；service folders 內附同樣資料供部署。
- `scripts/checkpoint.py`：先備份學員編輯，再還原指定 checkpoint。
- `workshop-output/`：Lab 1 的 evidence JSON、決策摘要與選做的 `finops-dashboard.html`，由學員產生、不提交 Git，也不屬於 source checkpoint。

完成課前安裝後，在 repository root：

```powershell
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
python -m finops_agent cost
python -m finops_agent brief --output .\workshop-output\lab1-evidence.json
```

bash：`PYTHONPATH=starter/src FINOPS_BACKEND=mock python -m finops_agent cost`。
基準答案為 MTD **4,760 net AI credits / USD 44.88**，部門第一名是 **AI Lab，2,400 credits / USD 26**。快照固定在 **`2026-09-22T23:59:59Z`**，MTD 是 **2026-09-01～2026-09-22**，不是今天。這次將合成月累計重新模擬為有高低變化的 22 天樣本，總數保留；若在 9/22 前查看，後續日期也是預先模擬的教學資料，不是預測或真實帳單。

把生成的 evidence JSON 附到 VS Code Copilot Chat 的 **Ask** 模式，用 Lab 1 的調查 prompts 找出有依據的行動。新版 `schema_version=2` 加入 `daily_usage`，每日 credits／USD 分別加總回上述 MTD；缺日不能補成零，完整口徑見 [資料說明](data/README.md)。`brief` 不會覆蓋舊檔；已有輸出時可改用 `--output workshop-output/lab1-evidence-v2.json`，並把新檔附到 Chat。

Lab 1 聚焦成本總覽、seat review、部門歸屬、預算與 what-if。完成決策摘要後，可依 [學員手冊的選做流程](docs/student-lab.md) 改用 Copilot **Agent** 模式，檢視它提議的 edits，僅建立 `workshop-output/finops-dashboard.html`。網頁用 File API 選取同一份新版 mock evidence；不用安裝套件、CDN、API key 或 server，也不讀真實組織資料。不修改 repo source／`.env`，不自動執行或上傳生成結果；dashboard 是 Lab 1 延伸，不增加 Lab 或核心 checkpoint。

Lab 2 接線後執行 `python -m finops_agent demo`，開啟終端提供的 User / Admin 兩個連結。User 扮演 carol：已用 USD 14、限額 20、剩餘 6；要求提高至 30 後先維持 pending，管理者確認後變成 **限額 30、剩餘 16**。不需複製 plan ID、token 或輸入 JSON。

Lab 3 只新增 **Foundry Model 切換**，不加入 Toolbox 或其他服務。依 [課前模型設定](docs/environment-prep.md#lab-3-foundry-model-課前準備) 選用既有 `foundry-identity`／`foundry-key` provider，重啟同一個本機 demo；SDK、個人工具、mock 資料和 admin approval 不變。呼叫 Foundry 模型不等於 Hosted Agent 已部署，原有 hosting 留作選配。

Foundry 的 `.env` 使用 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_API_KEY`、`MODEL_NAME`；key 模式選 `FINOPS_MODEL_PROVIDER=foundry-key`，identity 模式不需 API key。`MODEL_NAME` 填 Azure deployment name，GitHub Copilot 的認證與 `COPILOT_MODEL` 維持原本設定。

## 安全與邊界

預設 `FINOPS_BACKEND=mock`。Lab 1 的工具不需認證，但 Copilot Chat 需要 GitHub 登入；Lab 2 `ask` / `chat` 需要 SDK 的 Copilot 或 BYOK 認證。前兩個 Lab 不需 Azure hosting。SDK 自管 runtime，沒有額外 headless service 或自訂 Dockerfile。Lab 3 的 hosted 範例固定使用 mock、每次 invocation 獨立。

`demo` 只綁定 localhost，User / Admin 使用不同的啟動期 capability；模型只持有個人查詢／申請工具，沒有 approve。這是單機角色演示，不是正式登入系統。狀態重啟即重設；不要將此頁面或 admin link 公開，也不要把 demo 核准 API 部署到 Foundry。

真實 GitHub organization 資料／管理操作僅限 instructor CLI，寫入還需 write flag、有效的計畫核准及明確的人確認。**不提交 token、真實用量、公司資料、session history 或 audit logs。** Credits 不是原始 tokens；合成資料的價格不是正式 invoice。

Foundry Model 的 inference 費用由 Azure 計費，與 Agent 分析的 GitHub Copilot credits／budget 分開；提高 GitHub 限額不會改變 Azure quota，也不限制 Azure 支出。

Foundry 的個人環境、Managed Identity 與 remote invocation 需由主辦方課前準備；教材與本機演練不能替代活動環境的實際開通。
