# Checkpoint recovery

Lab 1 在 repo 根目錄的 VS Code Chat **Agent 模式**使用本專案的 [`/finops-investigation`](../../.github/skills/finops-investigation/SKILL.md)。核心成果是一頁原因、月底估算、三選二及不選理由的決策摘要；headroom 不是節省。選做單一 HTML dashboard 不增加 Lab，也不取代 Checkpoint 1。

唯一的程式 TODO 是 Lab 2 `demo_connection.py` 裡的 `build_demo_harness()`。個人工具、角色檢查、管理者核准與 browser UI 都已預建；starter 和 solution 使用相同介面。Lab 1 的 IDE terminal 調查不是這個 SDK 接線；Lab 2 allowlist 仍只有 `get_my_costs`、`get_my_savings`、`request_budget_increase`，沒有組織 workflow 證據或 approve 工具。

需要接回主線時，在 repo 根目錄只還原卡住的 Lab。工具會先把你的編輯備份到 `.workshop-backups/`：

```powershell
python .\scripts\checkpoint.py --lab 2
python -m pytest .\starter\checks -q
```

bash 將命令中的 `\` 換成 `/`。`--lab all` 還原 Lab 2 接線；`--lab 1` 為相容保留的 no-op。

Recovery 不刪 source 目錄，也不覆蓋 `.env` 或 `workshop-output/` 的成果。Lab 1 的 `lab1-evidence.json`、`finops-review.md`、選做 `finops-dashboard.html`（或另取的新檔名）都在 **source checkpoint 之外**；分析或圖表卡住時，請依 [學員手冊](../../docs/student-lab.md) 核對證據或先跳過選做，不必還原成果。

不要為了 recovery 在調查前讀完整答案包或先跑 `options`。Agent terminal 不可用時，由你啟用既有 venv、設定 `PYTHONPATH` 與 mock 變數，手動執行下一個唯讀命令、逐次貼給 Ask；不是重新實作工具。缺案例 fixture、未知 scope 或 `truncated=true` 請看 [疑難排解](../../docs/troubleshooting.md)，不要補零或改 source 繞過。

Recovery 不會重建 evidence。**完成調查與選擇後**，用 `python -m finops_agent --data-dir data brief --include-investigation --output workshop-output/lab1-evidence.json` 匯出，檔案已存在就換新名稱。一般 `brief` 不預載調查脈絡，缺 `investigation_evidence` 就重匯出，不猜情境；全體應為 **34,906.67 credits／USD 329.12**。

選做依 [`/finops-dashboard`](../../.github/skills/finops-dashboard/SKILL.md) 操作，只編輯 `workshop-output/finops-dashboard.html`（或新檔名），檢視後手動開啟，以 File API 載入 evidence；不新增外連、server 或管理操作。Skill 不需全域安裝，也不是權限沙箱；無法使用時見 [疑難排解](../../docs/troubleshooting.md)。

Lab 3 沿用同一個 harness 做 Foundry Model 切換，hosting 留作選配，也可觀摩講師 demo；沒有額外程式 TODO。整份課程仍是三個 Labs。
