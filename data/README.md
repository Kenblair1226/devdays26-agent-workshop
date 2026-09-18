# 合成教學資料（Synthetic workshop data）

這個目錄的人名、用量、價格與折扣都是虛構的。你可以拿來練習查核與視覺化，**不能把它當成真實帳戶資料、正式價格或帳單**。

| 檔案 | 用途 |
| --- | --- |
| `ai-credit-usage.json` | 已正規化的 organization billing AI-credit 用量 |
| `department-mapping.json` | 明確的 user → cost center／部門歸屬 |
| `users-28-day.ndjson` | 建議規則使用的行為用量指標 |
| `seats.json` | Mock Copilot seat 清單與最後 activity |
| `budgets.json` | Mock organization 與 user-level AI-credit budgets |

## 先對齊日期與資料範圍

- 快照固定為 **`2026-09-22T23:59:59Z`**，不是即時資料。`month_to_date` 固定涵蓋 **2026-09-01～2026-09-22（含首尾，共 22 天）**，不跟著電腦日期移動。
- 9 月用量是把既有的合成月累計**重新模擬為每天有高低變化的樣本**，保留原本教學案例的 MTD 總數，不是往真實觀測後面追加資料。若在 9/22 前查看，後續日期也是預先模擬的，**不是預測或未來真實觀測**。
- Billing 的 `coverage` 宣告 **2026-08-26～2026-09-22** 這個 28 天訓練視窗，`kind=sparse_training_samples`。8 月只提供 **2026-08-31** 的 carol 樣本（300 credits／USD 3），它不計入 9 月 MTD。其他未提供的 8 月日期不是已知的零。
- 9 月 22 個日期每天至少有一筆樣本，但這只表示「提供了這些日期的教學資料」，**不證明真實組織的帳務完整**。沒有提供的日期一律視為未知，不能自己補零。
- `users-28-day.ndjson` 也使用自己的固定 **2026-08-26～2026-09-22** 指標期間；不要把 28 天行為指標當成 9 月 MTD 帳務。

這些是內部 normalized teaching schemas，不是原封不動的 GitHub REST response。Net AI credits 不是原始 model tokens；billing 金額不包含 seat license fee 或 Azure hosting／inference 費用。

## 保留的基準答案

| MTD 範圍 | Net AI credits | Net USD |
| --- | --- | --- |
| 全體 | 4,760 | 44.88 |
| AI Lab | 2,400 | 26.00 |
| Platform Engineering | 800 | 6.92 |
| Security | 770 | 7.22 |
| Mobile | 700 | 4.20 |
| Unallocated | 90 | 0.54 |

全體 gross 為 4,900 credits／USD 46.32，discount 為 140 credits／USD 1.44；扣除後才是上述 net。模型種類不變，`gpt-5.4` 的 MTD net 仍為 2,580 credits。

部門彙總使用預先解析的 cost-center／主辦方 mapping；只有 user/team membership 並不等於可信的財務歸屬。不明用量保留在 `Unallocated`，不可為了讓排行好看而丟掉。

Seat activity 也要交叉查核：ivan 最後 activity 為 **2026-08-31**，距快照 22 天，但 MTD 仍有 90 credits；heidi 為 **2026-09-13**，距快照 9 天；judy 為 `null`，意思是未知。這些都不是自動回收 seat 的授權。

## Budget snapshot 與外推是另外兩件事

Organization budget 是 **限額 80／已用 45.20／剩餘 34.80**；carol 是 **限額 20／已用 14／剩餘 6**。Lab 2 經人核准後，carol 才變成 **限額 30／已用 14／剩餘 16**。每筆 budget 都有自己的 consumed snapshot，不要用 billing MTD 的 44.88 覆蓋它。

`forecast 80`／`run_rate_scenario` 只是線性外推：**44.88 ÷ 22 個已經過的快照日 × 30 天 = USD 61.20**，`projected_over_budget=false`。情境目前剩餘是 **80 − 44.88 = 35.12**，不等於實際 org budget 的 34.80，也不是保證月底花費。這個外推情境與「預先模擬的每日資料」不同。

What-if A 仍是同一個 9 月 MTD 期間內的 AI Lab USD 26 × 10% = **USD 2.60**；What-if B 是另外確認後，下個月回收 1 seat 的教學假設 **USD 19**。兩個期間與成本口徑不同，不合計成已實現節省。

## Lab 1 evidence 與選做 dashboard

在 repo 根目錄執行 `python -m finops_agent brief --output workshop-output/lab1-evidence.json`，會產生 `schema_version=2` 分析包。工具不覆蓋已有檔案；舊輸出可保留，改用 `--output workshop-output/lab1-evidence-v2.json` 重新產生，並在 Copilot 附件與網頁選檔時都選新檔。

新 section `daily_usage` 的契約如下：

| 欄位 | 語意 |
| --- | --- |
| `period` | `label=month_to_date`、`start=2026-09-01`、`end=2026-09-22` |
| `as_of`、`currency`、`unit`、`source` | 固定快照、`USD`、`AI credits` 與來源說明 |
| `granularity`、`coverage` | `daily_samples`；訓練視窗 2026-08-26～2026-09-22、`kind=sparse_training_samples` |
| `items` | 依日期排序的 22 筆日彙總；每筆只含 `date`、`net_quantity`、`net_amount` |
| `missing_dates` | 本次為 `[]`；只列缺少樣本的日期，不在 `items` 補零 |
| `limitations` | 來源與稀疏樣本的限制說明 |

`items` 的 credits 和 USD **各自**加總，須與 `cost_summary` 的 net 數字一致。日彙總沒有部門／模型維度，不能靠它臆造每日部門或模型 cross-filter；排行請讀 `department_ranking.ranking`、`model_breakdown.items`。Budget 與 seat 表仍讀各自的 section，不以 billing 或 forecast 代替。

[Lab 1 選做流程](../docs/student-lab.md) 會請 Copilot Agent 協助建立 `workshop-output/finops-dashboard.html`，由學員檢視後手動開啟，以瀏覽器 File API 選取 mock evidence。這是單一本機檔案，不是新增服務；舊 schema、損壞 JSON 或不一致資料應明確顯示錯誤。

## 資料副本

同樣的 JSON/NDJSON fixtures 也放在 `starter/data/` 與 `solution/data/`，讓部署包自含資料。維護教材時要保持三份語意一致，由 solution 的 checkpoint tests 檢查；不要只修改其中一份或把學員生成的 evidence 當作來源資料。

### 給教材維護者：檢查固定模擬資料

`scripts/generate_workshop_data.py` 使用 Python 標準函式庫，以固定規則把月累計分配成不同平日／週末的每日樣本，並同步三份 fixtures。維護者可以在 repo 根目錄用 `--check` 檢查資料與副本的一致性；這個模式只檢查，不改檔：

```powershell
python .\scripts\generate_workshop_data.py --check
```

bash 用 `python scripts/generate_workshop_data.py --check`。**學員直接使用現成資料，再用 `brief` 產生分析包就好，不需要執行生成器**；它不是 Lab 1 或選做 dashboard 的前置作業。
