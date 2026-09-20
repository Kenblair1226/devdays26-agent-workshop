# 唯讀工具速查

連結相對於 `SKILL.md`；命令則在 repo 根目錄執行。使用 `--data-dir data` 明確指定課程資料，避免讀入其他資料目錄。
不使用 `--instructor`、`ask`、`chat`、`approval-demo` 或其他管理命令。

## 終端準備

優先沿用學員已啟用的終端。若另開終端，只啟用既有環境，不重建或安裝。

PowerShell：

```powershell
& .\starter\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
$env:FINOPS_ALLOW_REAL_WRITES = "false"
```

bash：

```bash
source starter/.venv/bin/activate
export PYTHONPATH="$PWD/starter/src"
export FINOPS_BACKEND=mock
export FINOPS_ALLOW_REAL_WRITES=false
```

找不到環境或不是 Python 3.13，就停止並請學員回到環境準備，不自行安裝或改設定。

## 依問題選工具

以下命令兩種 shell 都可使用。將 `<部門>` 換成查詢得到的完整名稱，保留引號。

| 問題 | 命令 |
| --- | --- |
| 用量成長多少、從哪些部門來？ | `python -m finops_agent --data-dir data trend` |
| 當期各部門用量如何？ | `python -m finops_agent --data-dir data departments` |
| 候選部門的使用者分布？ | `python -m finops_agent --data-dir data breakdown --dimension user --department "<部門>"` |
| 候選部門的模型分布？ | `python -m finops_agent --data-dir data breakdown --dimension model --department "<部門>"` |
| 團隊的工作目標與成果定義？ | `python -m finops_agent --data-dir data roster "<部門>"` |
| 工作變多、單位成本變高，還是重複執行？ | `python -m finops_agent --data-dir data workflows "<部門>" --limit 6` |
| 依目前速率，月底可能用多少？ | `python -m finops_agent --data-dir data forecast 600` |

完成上述必要查核、進入選案階段後，才使用：

```text
python -m finops_agent --data-dir data options
```

## 讀結果時注意

- `trend` 的當期與比較期是不同月份、相同長度的模擬視窗，各有自己的 `period`、`as_of`。不改用 `previous_month` 湊比較資料。
- `workflows` 的 summary／by_user／by_workflow 涵蓋所選團隊該期全部已驗證 records；`--limit` 只限制顯示的 runs。
- 比較同一成功定義的 `successful_tasks`、`cost_per_successful_task_usd`、`credits_per_successful_task`。不要用執行次數冒充成功成果。
- 重複候選要核對 `input_revision`、`result_digest`、`model`、`trigger`、`status`，並確認業務真的只需要一份產物；人工或合規檢查不可直接移除。
- `forecast` 的 `projected_month_end_quantity` 與 `projected_month_end_amount` 分別是 credits 與金額。USD 600 是估算情境，不取代實際 budget 餘額。
- `options` 的歷史機會、未來估算、`additional_headroom_usd` 分開解讀。模型試跑不是全體任務的保證；未通過品質條件就保留未估計。
- 工具失敗、範圍不支援或資料缺漏就說明；不換成真實 backend、不讀原始檔猜答案、不補零。

## 決策完成之後

完整 evidence 匯出留給學員在選做 dashboard 前手動執行 `brief --include-investigation`。
它不是調查開場的輸入；這個調查 skill 不會預先載入那份答案包。
