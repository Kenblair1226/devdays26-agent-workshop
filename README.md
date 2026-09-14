# Copilot FinOps Agent Workshop

以 **Python 3.13 + GitHub Copilot SDK + Microsoft Foundry**，在 90 分鐘內帶約 40 位學員完成可查詢費用、分析部門用量、提出節省建議及管理 seat/budget 計畫的 Agent。

| Lab | Hands-on | 執行位置 |
| --- | --- | --- |
| 1 | 用現成工具 + Copilot Chat 調查成本、seats、budgets，交付決策摘要 | 本機 mock 資料；Chat 需 GitHub 登入，免寫程式 |
| 2 | 一次 harness 接線：查費用／節省建議 → 申請提高限額 → 管理者 approve | 本機使用者／管理者頁面，Copilot 或 BYOK model |
| 3 | 同一個 harness 換成 Foundry Model，再選配 direct-code deploy | 預建模型；時間或資源不足改講師 demo |

**學員入口：[環境準備](docs/environment-prep.md) → [學員手冊](docs/student-lab.md)。**
講師請先讀 [90 分鐘 runbook](docs/instructor-guide.md)，並參考 [架構](docs/architecture.md) 與 [疑難排解](docs/troubleshooting.md)。[intro.md](intro.md) 保留中英文活動簡介。

## Repository

- `starter/`：Lab 1 tools 全數可用；Lab 2 只在 `demo_connection.py` 留一個 harness factory TODO。
- `solution/`：完整參考實作與 tests，和 starter 使用相同介面。
- `data/`：合成、已正規化的教學報表；service folders 內附同樣資料供部署。
- `scripts/checkpoint.py`：先備份學員編輯，再還原指定 checkpoint。
- `workshop-output/`：Lab 1 的 evidence JSON 與 Copilot 決策摘要，由學員產生、不提交 Git。

完成課前安裝後，在 repository root：

```powershell
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
python -m finops_agent cost
python -m finops_agent brief --output .\workshop-output\lab1-evidence.json
```

bash：`PYTHONPATH=starter/src FINOPS_BACKEND=mock python -m finops_agent cost`。
基準答案為 MTD **4,760 net AI credits / USD 44.88**，部門第一名是 **AI Lab，2,400 credits**。把生成的 evidence JSON 附到 VS Code Copilot Chat，用 Lab 1 的調查 prompts 分析；不必先實作 aggregation 或 SDK。

Lab 1 聚焦成本總覽、seat review、部門歸屬、預算與 what-if。課程使用現成工具與合成資料，不需要額外安裝分析平台、設定 SSO 或同步真實組織資料。

Lab 2 接線後執行 `python -m finops_agent demo`，開啟終端提供的 User / Admin 兩個連結。User 扮演 carol：已用 USD 14、限額 20、剩餘 6；要求提高至 30 後先維持 pending，管理者確認後變成 **限額 30、剩餘 16**。不需複製 plan ID、token 或輸入 JSON。

Lab 3 只新增 **Foundry Model 切換**，不加入 Toolbox 或其他服務。依 [課前模型設定](docs/environment-prep.md#lab-3-foundry-model-課前準備) 選用既有 `foundry-identity`／`foundry-key` provider，重啟同一個本機 demo；SDK、個人工具、mock 資料和 admin approval 不變。呼叫 Foundry 模型不等於 Hosted Agent 已部署，原有 hosting 留作選配。

## 安全與邊界

預設 `FINOPS_BACKEND=mock`。Lab 1 的工具不需認證，但 Copilot Chat 需要 GitHub 登入；Lab 2 `ask` / `chat` 需要 SDK 的 Copilot 或 BYOK 認證。前兩個 Lab 不需 Azure hosting。SDK 自管 runtime，沒有額外 headless service 或自訂 Dockerfile。Lab 3 的 hosted 範例固定使用 mock、每次 invocation 獨立。

`demo` 只綁定 localhost，User / Admin 使用不同的啟動期 capability；模型只持有個人查詢／申請工具，沒有 approve。這是單機角色演示，不是正式登入系統。狀態重啟即重設；不要將此頁面或 admin link 公開，也不要把 demo 核准 API 部署到 Foundry。

真實 GitHub 操作僅限 instructor CLI，寫入還需 write flag、有效的計畫核准及明確的人確認。**不提交 token、公司資料、session history 或 audit logs。** Credits 不是原始 tokens；合成資料的價格不是正式 invoice。

Foundry Model 的 inference 費用由 Azure 計費，與 Agent 分析的 GitHub Copilot credits／budget 分開；提高 GitHub 限額不會改變 Azure quota，也不限制 Azure 支出。

Foundry 的個人環境、Managed Identity 與 remote invocation 需由主辦方課前準備；教材與本機演練不能替代活動環境的實際開通。
