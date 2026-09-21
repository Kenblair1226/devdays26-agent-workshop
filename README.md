# Copilot FinOps Agent Workshop

以 **Python 3.13 + GitHub Copilot SDK + Microsoft Foundry**，帶約 40 位學員透過三個 Labs，從「用量變多」一路查到工作量、成功成果與可行的改善，再體驗人工核准。

> 本月 AI credits 成長異常。請找出主要原因，預估月底用量，提出兩個改善方案

不要把最高用量直接判成浪費。讓觀眾看見證據逐步收斂，再從「修正重複觸發、簡單任務換模型、暫時提高預算」選兩個、說明取捨；headroom 是業務支援，不是節省。

| Lab | Hands-on | 執行位置 |
| --- | --- | --- |
| 1 | Copilot Chat Agent 按需使用現成唯讀工具：每日趨勢 → user/model → 團隊／workflow；交付原因、預測、兩方案摘要，選做 dashboard | 本機 mock 資料；Copilot Chat 使用既有 GitHub 登入 |
| 2 | 一次 harness 接線：查費用／節省建議 → 申請提高限額 → 管理者 approve；選配改用 Foundry Model 重跑 | 本機使用者／管理者頁面，Copilot 或 BYOK model |
| 3（選配） | 將同一個 Agent direct-code deploy 到 Foundry Hosted Agent | 預建 hosting 環境；依學員進度選擇實作或講師 demo |

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
$env:FINOPS_ALLOW_REAL_WRITES = "false"
python -m finops_agent --data-dir data cost
python -m finops_agent --data-dir data trend
```

bash：`PYTHONPATH=starter/src FINOPS_BACKEND=mock python -m finops_agent --data-dir data cost`。
MTD 為 **34,906.67 net AI credits / USD 329.12**，部門第一名是 **AI Lab，17,600 credits / USD 190.67**。快照固定在 **`2026-09-22T23:59:59Z`**，期間為 **2026-09-01～2026-09-22**。全部都是預先模擬的教學資料，不是即時用量、實測或真實帳單，也不支持季節性推論。

Clone 後在 VS Code 開啟 **repo 根目錄**，Chat 選 **Agent**，輸入 `/finops-investigation 本月 AI credits 成長異常。請找出主要原因，預估月底用量，提出兩個改善方案`。本專案的 [調查 skill](.github/skills/finops-investigation/SKILL.md) 提供工具目錄與逐步揭露規則，不先附完整 brief 或教師答案。無須全域安裝；skill 不是權限沙箱，仍須檢視命令。這是 IDE terminal 調查，不是 Python SDK 接線；操作與備案見 [學員手冊](docs/student-lab.md)。

比較期來自獨立的 2026-08-01～2026-08-22 fixture（21,523.33 credits／USD 188.25）；普通 billing `previous_month` 不支援。兩期各 22 個日曆日，成長 13,383.33 credits（62.18%）／USD 140.87（74.83%）先用原始彙總計算，顯示值相減可能差 0.01。`forecast 600` 的 47,600 AI credits／USD 448.80 是歷史 MTD 線性 run-rate，不是工作量調整後的保證。

Checkpoint 1 是 `workshop-output/finops-review.md`：有證據的原因、月底估算、A／B／C 中兩個選擇與一個不選的理由，包含 owner、品質 gate、期間與假設。先查 workload/outcome，再用唯讀 `options` 比較；seat review 與 Unallocated 留在會計限制／延伸追問，不強制回收。

**完成決策後**才執行 `python -m finops_agent --data-dir data brief --include-investigation --output workshop-output/lab1-evidence.json`；檔案已存在就換新名稱。一般 `brief` 不預載調查脈絡。選做時輸入 `/finops-dashboard 用 workshop-output/lab1-evidence.json 製作本機 dashboard`，由 [dashboard skill](.github/skills/finops-dashboard/SKILL.md) 提供驗證與 Clawpilot 樣式規則。檢視 edits 後只建立單一 HTML，以 File API 載入 JSON；無外連、CDN、server 或管理操作，不自動執行或上傳。它不增加 Lab 或 checkpoint；資料口徑見 [資料說明](data/README.md)。

Lab 2 接線後執行 `python -m finops_agent demo`，開啟終端提供的 User / Admin 兩個連結。用 C 的 migration 業務理由演練（不要求小組一定選 C）：carol 9/30 前剩 60 批次、估計還需 USD 61.60，個人計畫總額約 164.27。User 已用 USD 102.67、限額 150、剩餘 47.33；要求提高至 220 後先維持 pending、額度不變，人確認 scope、hard stop 與 review／expiry 後才變成 **限額 220、已用 102.67 不變、剩餘 117.33**。增加 70 是 headroom，節省 0；mock `expires_at` 不代表自動回復。只提供 `get_my_costs`、`get_my_savings`、`request_budget_increase`，沒有組織調查或 approve 工具，不需複製 plan ID、token 或輸入 JSON。

Lab 2 完成核心流程後，可依 [課前模型設定](docs/environment-prep.md#lab-2-選配foundry-model-課前準備) 選用既有 `foundry-identity`／`foundry-key` provider，重啟同一個本機 demo；SDK、個人工具、mock 資料和 admin approval 不變。這只是 Lab 2 的選配 model switch，不等於 Hosted Agent 已部署。

Lab 3 是獨立的 [Foundry Hosted Agent 部署](docs/hosted-deployment.md)，使用 direct-code hosting；只有主辦方已備妥環境時才實作，否則觀摩講師 demo。不加入 Toolbox 或其他服務。

Foundry 的 `.env` 使用 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_API_KEY`、`MODEL_NAME`；key 模式選 `FINOPS_MODEL_PROVIDER=foundry-key`，identity 模式不需 API key。`MODEL_NAME` 填 Azure deployment name，GitHub Copilot 的認證與 `COPILOT_MODEL` 維持原本設定。

## 安全與邊界

預設 `FINOPS_BACKEND=mock`。Lab 1 的工具不需認證，但 Copilot Chat 需要 GitHub 登入；Lab 2 `ask` / `chat` 需要 SDK 的 Copilot 或 BYOK 認證。Lab 1、Lab 2 核心流程與 Lab 2 的本機 Foundry model switch 都不需 Azure hosting。SDK 自管 runtime，沒有額外 headless service 或自訂 Dockerfile。Lab 3 的 hosted 範例固定使用 mock、每次 invocation 獨立。

`demo` 只綁定 localhost，User / Admin 使用不同的啟動期 capability；模型只持有個人查詢／申請工具，沒有 approve。這是單機角色演示，不是正式登入系統。狀態重啟即重設；不要將此頁面或 admin link 公開，也不要把 demo 核准 API 部署到 Foundry。

真實 GitHub organization 資料／管理操作僅限 instructor CLI，寫入還需 write flag、有效的計畫核准及明確的人確認。**不提交 token、真實用量、公司資料、session history 或 audit logs。** Credits 不是原始 tokens；合成資料的價格不是正式 invoice。

Foundry Model 的 inference 費用由 Azure 計費，與 Agent 分析的 GitHub Copilot credits／budget 分開；提高 GitHub 限額不會改變 Azure quota，也不限制 Azure 支出。

Foundry 的個人環境、Managed Identity 與 remote invocation 需由主辦方課前準備；教材與本機演練不能替代活動環境的實際開通。
