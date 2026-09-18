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
- 9 月用量以原始 **2026-09-01～2026-09-03** 三天合成資料為基準，**用量與金額都乘上 22 / 3**：4,760 × 22 / 3 = **34,906.67 net AI credits**；USD 44.88 × 22 / 3 = **USD 329.12**。不是把三天總數重新分攤到 22 天。
- 保留 9/1～9/3 的來源資料列；三天活動模式重複 **7 個週期（9/1～9/21）**，9/22 再取**各 user/model 的三天平均**。這是教學用的**線性外推**，不是實測或經驗證的預測，也沒有平日／週末季節性模型。若在 9/22 前查看，後續日期同樣是預先模擬，不是真實帳戶的未來觀測。
- Billing 的 `coverage` 宣告 **2026-08-26～2026-09-22** 這個 28 天訓練視窗，`kind=sparse_training_samples`。8 月只提供 **2026-08-31** 的 carol 樣本（300 credits／USD 3），它不計入 9 月 MTD。其他未提供的 8 月日期不是已知的零。
- 9 月 22 個日期每天至少有一筆樣本，但這只表示「提供了這些日期的教學資料」，**不證明真實組織的帳務完整**。沒有提供的日期一律視為未知，不能自己補零。
- `users-28-day.ndjson` 使用自己的固定 **2026-08-26～2026-09-22** 指標期間。`ai_credits_used` 以各使用者原始三天平均 × 28 天產生，carol 為 **13,066.67 credits**；`active_days` 與其他行為計數仍是獨立的合成 28 天觀察，不按 22 / 3 放大，更不能讓 active days 超過 28。不要把這個視窗的指標當成 9 月 MTD 帳務。

這些是內部 normalized teaching schemas，不是原封不動的 GitHub REST response。Net AI credits 不是原始 model tokens；billing 金額不包含 seat license fee 或 Azure hosting／inference 費用。

## 外推到 9/22 的基準答案

| MTD 範圍 | Net AI credits | Net USD |
| --- | --- | --- |
| 全體 | 34,906.67 | 329.12 |
| AI Lab | 17,600.00 | 190.67 |
| Platform Engineering | 5,866.67 | 50.75 |
| Security | 5,646.67 | 52.95 |
| Mobile | 5,133.33 | 30.80 |
| Unallocated | 660.00 | 3.96 |

全體 gross 為 **35,933.33 credits／USD 339.68**，discount 為 **1,026.67 credits／USD 10.56**；原始精度下 gross − discount = net。模型種類不變：

| 模型 | MTD net AI credits | MTD net USD |
| --- | --- | --- |
| `gpt-5.4` | 18,920.00 | 189.20 |
| `gpt-5-mini` | 8,653.33 | 51.92 |
| `claude-opus-5` | 7,333.33 | 88.00 |

原始資料保留小數精度，**先加總再四捨五入，顯示兩位小數**。各部門／模型／使用者的小計獨立四捨五入，可能與全體差 **0.01 credit／USD 0.01**：模型 credits 顯示值相加是 **34,906.66**，部門金額顯示值相加是 **USD 329.13**，但全體必須仍是 **34,906.67／USD 329.12**，不能為了湊齊已取整的小計而改掉總額。已顯示的 gross credits 減 discount credits 也會比 net 少 0.01；原始精度的等式沒有破壞。請保留 metadata 的 `rounding_note`，跨維度核對採有界的四捨五入容差，不把這個差異當成資料毀損。

部門彙總使用預先解析的 cost-center／主辦方 mapping；只有 user/team membership 並不等於可信的財務歸屬。不明用量保留在 `Unallocated`，不可為了讓排行好看而丟掉。

Seat activity 也要交叉查核：ivan 最後 activity 為 **2026-08-31**，距快照 22 天，但 MTD 仍有 **660 credits**；heidi 為 **2026-09-13**，距快照 9 天；judy 為 `null`，意思是未知。這些都不是自動回收 seat 的授權。

## Budget snapshot 與外推是另外兩件事

Organization budget 是 **限額 600／已用 331.47／剩餘 268.53**；carol 的 MTD billing 為 **10,266.67 credits／USD 102.67**，user budget 是 **限額 150／已用 102.67／剩餘 47.33**。申請提高至 220 時先維持 pending 和原額度；Lab 2 經人核准後，carol 才變成 **限額 220／已用 102.67 不變／剩餘 117.33**。

教學上限是以原始 9/1～9/3 情境的 user USD 20、org USD 80 乘上 22 / 3，再向上調整成便於操作的整數 USD 150、600；申請目標則是原始 USD 30 × 22 / 3 = USD 220。Org 的獨立 consumed 基準是原始 USD 45.20 × 22 / 3，顯示為 USD 331.47。每筆 budget 都有自己的 consumed snapshot，**不要用 billing MTD 的 USD 329.12 覆蓋它**。

`forecast 600`／`run_rate_scenario` 是另一個月末 run-rate 情境：**329.12 ÷ 22 個已經過的快照日 × 30 天 = USD 448.80**，`projected_over_budget=false`。情境目前剩餘是 **600 − 329.12 = 270.88**，不等於實際 org budget 的 268.53，也不是保證月底花費。這與前面「從三天基準產生 22 天合成資料」的線性外推是不同用途；`forecast` 仍可接其他自訂情境金額。

What-if A 是同一個 **9/1～9/22** 期間內的 AI Lab USD 190.67 × 10%，顯示差額為 **USD 19.07**；What-if B 是另外確認後，下個月回收 1 seat 的教學假設 **USD 19**。兩個期間與成本口徑不同，不合計成已實現節省。

## Lab 1 evidence 與選做 dashboard

在 repo 根目錄執行 `python -m finops_agent brief --output workshop-output/lab1-evidence.json`，會產生 `schema_version=2` 分析包。**更新資料後必須重新產生 evidence**：舊檔可能同樣有 schema 2、`daily_usage` 與 9/22 快照，單靠日期或 schema 無法辨識錯誤的舊總額。工具不覆蓋已有檔案；保留舊輸出，改用 `--output workshop-output/lab1-evidence-v3.json`，並在 Copilot 附件與網頁選檔時都選新檔，再核對全體 34,906.67／329.12。

新 section `daily_usage` 的契約如下：

| 欄位 | 語意 |
| --- | --- |
| `period` | `label=month_to_date`、`start=2026-09-01`、`end=2026-09-22` |
| `as_of`、`currency`、`unit`、`source` | 固定快照、`USD`、`AI credits` 與來源說明 |
| `granularity`、`coverage` | `daily_samples`；訓練視窗 2026-08-26～2026-09-22、`kind=sparse_training_samples` |
| `items` | 依日期排序的 22 筆日彙總；每筆只含 `date`、`net_quantity`、`net_amount` |
| `missing_dates` | 本次為 `[]`；只列缺少樣本的日期，不在 `items` 補零 |
| `limitations` | 來源與稀疏樣本的限制說明 |

這個重複模式下，`items` 的每日顯示值以兩位小數**各自**加總，credits 與 USD 都恰好對回 `cost_summary` 的 net 數字；每日檢核與跨維度小計的四捨五入容差要分開處理。日彙總沒有部門／模型維度，不能靠它臆造每日部門或模型 cross-filter；排行請讀 `department_ranking.ranking`、`model_breakdown.items`。Budget 與 seat 表仍讀各自的 section，不以 billing 或 forecast 代替。

[Lab 1 選做流程](../docs/student-lab.md) 會請 Copilot Agent 協助建立 `workshop-output/finops-dashboard.html`，由學員檢視後手動開啟，以瀏覽器 File API 選取新產生的 mock evidence。這是單一本機檔案，不是新增服務；舊 schema、損壞 JSON 或超出四捨五入容差的不一致資料應明確顯示錯誤。

## 資料副本

同樣的 JSON/NDJSON fixtures 也放在 `starter/data/` 與 `solution/data/`，讓部署包自含資料。維護教材時要保持三份語意一致，由 solution 的 checkpoint tests 檢查；不要只修改其中一份或把學員生成的 evidence 當作來源資料。

### 給教材維護者：檢查固定模擬資料

`scripts/generate_workshop_data.py` 使用 Python 標準函式庫，保留原始三天來源列作為第 1 個週期，三天模式共 7 個週期、加上 9/22 的各 user/model 平均，保留原始小數精度並同步三份 fixtures。沒有平日／週末權重。9 月 billing 是 **7 × 11 + 9 = 86 筆**，這是維護者的資料檢查，不是學員需要背的答案。維護者可以在 repo 根目錄用 `--check` 檢查資料與副本的一致性；這個模式只檢查，不改檔：

```powershell
python .\scripts\generate_workshop_data.py --check
```

bash 用 `python scripts/generate_workshop_data.py --check`。**學員直接使用現成資料，再用 `brief` 產生分析包就好，不需要執行生成器**；它不是 Lab 1 或選做 dashboard 的前置作業。
