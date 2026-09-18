# Checkpoint recovery

Lab 1 用現成 tools 與 GitHub Copilot Chat 調查資料，核心成果是一頁 FinOps 決策摘要。想延伸呈現方式，可以選做由 Copilot Agent 協助建立的網頁 dashboard；它不增加 Lab，也不取代 Checkpoint 1。

唯一的程式 TODO 是 Lab 2 `demo_connection.py` 裡的 `build_demo_harness()`。個人工具、角色檢查、管理者核准與 browser UI 都已預建；starter 和 solution 使用相同介面。

需要接回主線時，在 repo 根目錄只還原卡住的 Lab。工具會先把你的編輯備份到 `.workshop-backups/`：

```powershell
python .\scripts\checkpoint.py --lab 2
python -m pytest .\starter\checks -q
```

bash 將命令中的 `\` 換成 `/`。`--lab all` 還原 Lab 2 接線；`--lab 1` 為相容保留的 no-op。

Recovery 不刪 source 目錄，也不覆蓋 `.env` 或 `workshop-output/` 的成果。Lab 1 的 `lab1-evidence.json`、`finops-review.md`、選做 `finops-dashboard.html`（或另取的新檔名）都在 **source checkpoint 之外**；分析或圖表卡住時，請依 [學員手冊](../../docs/student-lab.md) 核對證據或先跳過選做，不必還原成果。

Lab 3 沿用同一個 harness 做 Foundry Model 切換，hosting 留作選配，也可觀摩講師 demo；沒有額外程式 TODO。整份課程仍是三個 Labs。
