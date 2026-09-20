# 合成教學資料（Synthetic workshop data）

這個目錄的人名、用量、價格、折扣、工作紀錄與 pilot 全部虛構、預先模擬，**不是真實帳戶資料、正式價格或帳單**。本頁包含案例答案；Lab 1 從 [調查 skill](../.github/skills/finops-investigation/SKILL.md) 開始，完成按需調查後再讀這些細節，不把本頁當成初始答案附件。

| 檔案 | 用途 |
| --- | --- |
| `ai-credit-usage.json` | 已正規化的 organization billing AI-credit 用量 |
| `department-mapping.json` | 明確的 user → cost center／部門歸屬 |
| `users-28-day.ndjson` | 建議規則使用的行為用量指標 |
| `seats.json` | Mock Copilot seat 清單與最後 activity |
| `budgets.json` | Mock organization 與 user-level AI-credit budgets |
| `usage-comparison.json` | 獨立的 8/1～8/22 matched baseline 與當期比較 metadata；供 `trend`，不是普通 billing 的 coverage |
| `team-roster.json` | 合成團隊 members、initiative、success_definition、deadline、planned_remaining_tasks；按團隊查詢，不是真實 org lookup |
| `workflow-runs.json` | 兩期完整合成 run ledger；按 date/user/model 對回當期 billing／獨立 baseline，提供 workload、outcome 與 trigger 證據 |
| `model-pilots.json` | 獨立的同任務模型比較 pilot，含品質檢查與成本；不併入組織 billing，也不是公開模型價格 |

## 先對齊日期與資料範圍

- 快照固定為 **`2026-09-22T23:59:59Z`**，不是即時資料。`month_to_date` 固定涵蓋 **2026-09-01～2026-09-22（含首尾，共 22 天）**，不跟著電腦日期移動。
- MTD 合計 **34,906.67 net AI credits／USD 329.12**。所有日期預先模擬，不是實測或經驗證的預測，不支持季節性推論。
- Billing 的 `coverage` 宣告 **2026-08-26～2026-09-22** 這個 28 天訓練視窗，`kind=sparse_training_samples`。8 月只提供 **2026-08-31** 的 carol 樣本（300 credits／USD 3），它不計入 9 月 MTD。其他未提供的 8 月日期不是已知的零。
- 獨立比較來源 `usage-comparison.json` 的 baseline 是 **2026-08-01～2026-08-22**、`as_of=2026-08-22T23:59:59Z`；current 是 **2026-09-01～2026-09-22**、`as_of=2026-09-22T23:59:59Z`。各 22 個日曆日，不是完整月份。普通 billing `previous_month` 不支援，請用 `trend`；比較 fixture 不是完整 8 月帳務。
- 9 月 22 個日期每天至少有一筆樣本，但這只表示「提供了這些日期的教學資料」，**不證明真實組織的帳務完整**。沒有提供的日期一律視為未知，不能自己補零。
- `users-28-day.ndjson` 使用獨立的 **2026-08-26～2026-09-22** 指標期間，carol 的 `ai_credits_used` 為 **13,066.67 credits**；`active_days` 不超過 28。不要把這個視窗的指標當成 9 月 MTD 帳務。

這些是內部 normalized teaching schemas，不是原封不動的 GitHub REST response。Net AI credits 不是原始 model tokens；billing 金額不包含 seat license fee 或 Azure hosting／inference 費用。

## 9/22 快照的 MTD 答案

| MTD 範圍 | Net AI credits | Net USD |
| --- | --- | --- |
| 全體 | 34,906.67 | 329.12 |
| AI Lab | 17,600.00 | 190.67 |
| Platform Engineering | 5,866.67 | 50.75 |
| Security | 5,646.67 | 52.95 |
| Mobile | 5,133.33 | 30.80 |
| Unallocated | 660.00 | 3.96 |

全體 gross 為 **35,933.33 credits／USD 339.68**，discount 為 **1,026.67 credits／USD 10.56**；原始精度下 gross − discount = net。模型彙總如下：

| 模型 | MTD net AI credits | MTD net USD |
| --- | --- | --- |
| `gpt-5.4` | 18,920.00 | 189.20 |
| `gpt-5-mini` | 8,653.33 | 51.92 |
| `claude-opus-5` | 7,333.33 | 88.00 |

原始資料保留小數精度，**先加總再四捨五入，顯示兩位小數**。各部門／模型／使用者的小計獨立四捨五入，可能與全體差 **0.01 credit／USD 0.01**：模型 credits 顯示值相加是 **34,906.66**，部門金額顯示值相加是 **USD 329.13**，但全體必須仍是 **34,906.67／USD 329.12**，不能為了湊齊已取整的小計而改掉總額。已顯示的 gross credits 減 discount credits 也會比 net 少 0.01；原始精度的等式沒有破壞。請保留 metadata 的 `rounding_note`，跨維度核對採有界的四捨五入容差，不把這個差異當成資料毀損。

部門彙總使用預先解析的 cost-center／主辦方 mapping；只有 user/team membership 並不等於可信的財務歸屬。不明用量保留在 `Unallocated`，不可為了讓排行好看而丟掉。

Seat activity 也要交叉查核：ivan 最後 activity 為 **2026-08-31**，距快照 22 天，但 MTD 仍有 **660 credits**；heidi 為 **2026-09-13**，距快照 9 天；judy 為 `null`，意思是未知。這些都不是自動回收 seat 的授權。

## 案例調查：先有線索，再取業務證據

`python -m finops_agent --data-dir data trend`／`get_daily_usage_trend()` 回傳 `current`／`baseline` 每日序列、`current_summary`／`baseline_summary`、`change` 與 `department_changes`。它**不載入 roster、workflow 或 pilot，不直接揭露原因**。當期為 34,906.67 credits／USD 329.12，比較期為 21,523.33／188.25；先算原始彙總再取整的成長是 **13,383.33 credits（62.18%）／USD 140.87（74.83%）**。不要用已取整顯示值相減去修正最後 0.01。

AI Lab 貢獻 **10,560 credits／USD 114.40** 的增加，Security 貢獻 **2,823.33／26.47**，其他群組不變（含 Unallocated）。`departments`、`breakdown --dimension user|model --department '<部門>'` 接著縮小範圍；`user|model` 表示兩種選項，執行時選其中一個。

| 按需工具 | 回應契約 |
| --- | --- |
| `roster '<部門>'`／`get_team_roster(department)` | 只回指定 `team` 及 source／metadata；成員與財務 mapping 驗證一致，但不表示任意 org membership 可當 cost center |
| `workflows '<部門>' --limit 6`／`get_workflow_evidence(department, limit)` | `current`／`baseline` 各有 period、summary、by_user、by_workflow、runs、returned_runs、total_runs、truncated、summary_scope；limit 必須 1..20 |
| `options`／`compare_improvement_options()` | 調查後才按需取得比較所需的業務／pilot 脈絡；唯讀 conditional estimates，不建立 plan、approval 或任何寫入 |

`runs` 是展示樣本，含 run_id、started_at、user、workflow、task_id、input_revision、result_digest、trigger、status、model、net_quantity／net_amount。`summary`、`by_user`、`by_workflow` 一律涵蓋該團隊該期**全部驗證過的 runs**，不只 `--limit 6` 的六筆。完整 ledger 對回各日期／使用者／模型原始帳務；未知團隊、缺資料、不合法 limit 明確報錯，不捏造零。四個調查工具僅供一般 mock SDK toolset，real adapter 不臆造業務資料；Lab 2 個人三工具 allowlist 不變。

### Workload／outcome 反轉（調查後核對）

- **AI Lab／legacy platform migration，carol、dave**：baseline **80** 個成功批次 → current **200**（工作量 +150%），credits **7,040 → 17,600**、USD **76.27 → 190.67** 同增 150%。成功定義是一批通過 regression checks；原始平均每成功批次 **USD 0.953333／88 credits** 不變。高成本有工作量解釋，不代表所有 production migration 都有效率。
- **Security／automated-review，grace、heidi**：baseline **30 runs／30 個不同成功 PR revision**，current **60 runs／仍 30 個成果**。`successful_tasks` 按 workflow／task／input_revision 去重，與 successful_attempts 不同；每成果 USD **0.882444 → 1.764889**。
- 重複成功候選共 **30**：同 workflow、task_id、input_revision、result_digest **及 model**，先 `pull_request` trigger 再 `push`。政策每 PR revision 只需一份自動產物；保留獨立人工／合規 checks。失敗重試、revision 變更或不同模型輸出不自動是冗餘；須由 workflow owner 確認 dedup key 和 artifact。
- **Platform Engineering／Alice 的 gpt-5.4 simple-maintenance cohort**已觀察成本 **USD 38.87**。`model-pilots.json` 另有 fictional matched pilot：20 個相同簡單任務，baseline **20/20** 通過、成本 **USD 2**；mini **20/20** 通過、**USD 1.20**。貨幣成本比 0.6（低 40%），不是組織 billing、不是每個任務可切換的證明，也不能推論 token／credit 比率。

每成果成本須在相同成功定義內比較；不可跨工作類型評分個人生產力。Workflow 的比率採原始成本計算，不用已取整的 USD 190.67 等顯示值反推。

## Budget snapshot 與外推是另外兩件事

Organization budget 是 **限額 600／已用 331.47／剩餘 268.53**；carol 的 MTD billing 為 **10,266.67 credits／USD 102.67**，user budget 是 **限額 150／已用 102.67／剩餘 47.33**。申請提高至 220 時先維持 pending 和原額度；Lab 2 經人核准後，carol 才變成 **限額 220／已用 102.67 不變／剩餘 117.33**。

每筆 budget 都有自己的 consumed snapshot，**不要用 billing MTD 的 USD 329.12 覆蓋它**。

`forecast 600`／`run_rate_scenario` 是月末 run-rate 情境：**329.12 ÷ 22 個已經過的快照日 × 30 天 = USD 448.80**，`projected_over_budget=false`。`projected_month_end_quantity=47600` AI credits、`projected_month_end_amount=448.80` USD，採歷史 MTD 線性外推，不是 workload-adjusted 保證。情境目前剩餘是 **600 − 329.12 = 270.88**，不等於實際 org budget 的 268.53，也不是保證月底花費；`forecast` 可接其他自訂情境金額。

## 三個條件式方案：選兩個，不把 headroom 當節省

`options` 回傳的 `period` 是 2026-09-01～2026-09-22；`remaining_period` 是 **2026-09-23～2026-09-30，共 8 日**。這是選擇之後仍需 owner 確認的 what-if，不是已實現效益。

| 選項 ID | 已觀察期間的反事實機會 | 剩餘期間的條件式估算 | 限制 |
| --- | --- | --- | --- |
| `deduplicate_triggers` | USD 26.47／2,823.33 credits | USD 9.63／1,026.67 AI credits，兩個單位分開 | 重複率維持；只去除不需要的成功產物，保留失敗重試與必要 checks，已發生花費不退款 |
| `simple_task_model` | 合格 simple-maintenance cohort 的 USD 15.55 | USD 5.65 | Pilot 可代表後續、品質相同與 rollback gate 成立；不全面降級 migration，`estimated_credit_savings=null` |
| `temporary_budget` | carol 的 user limit 150 → 220 | headroom +USD 70，`estimated_savings_usd=0` | 需人核准 scope、限額、hard stop、review／expiry；不減少 credits、過去成本、組織或 Azure 費用 |

模型方案 B 只將 pilot 的貨幣成本比 0.6 套到符合條件的 USD 38.87 cohort；品質 gate 失敗時沒有量化 savings 建議，不推論 raw token 或 credit savings。A/B cohorts 不重疊，假設成立時**同一剩餘期間**合計 **USD 15.28**；不能把歷史機會加到未來估算，也不能加上 C 的 headroom。

方案 A 的 `remaining_month_credit_savings=1026.67` 是相同重複率下、剩餘 8 日的條件式 AI-credit 估算，不與 USD 相加，也不補齊 B 的 credit savings。B 的 `estimate_status` 為 `conditional_pilot_estimate`（同品質、較便宜，但仍需驗證代表性）、`quality_gate_failed` 或 `not_cheaper`；後兩者的 `observed_period_opportunity_usd`、`remaining_month_savings_usd` 為 null，組合估算也為 null。成功 pilot 下的 `estimated_credit_savings` 仍是 null。

C 的工作計畫：carol 當期 **100** 個成功 migration 批次、原始成本 **USD 102.666667**，9/30 前還有 **60** 批次，估計剩餘成本 **USD 61.60**；個人 budget consumed 102.67 + 61.60 ≈ **164.27**，比限額 150 高 **14.27**。這是 plan-based personal estimate，不是組織歷史 run-rate。220 是提案，不保證把多出的 70 全花完；`expires_at` 9/30 是 mock metadata，不提供 production 自動回復／timer。

## Lab 1 evidence 與選做 dashboard

**完成調查與兩方案選擇後**，執行 `python -m finops_agent --data-dir data brief --include-investigation --output workshop-output/lab1-evidence.json` 匯出 `schema_version=2` 分析包。一般 `brief` 不預載業務脈絡，只有旗標才加入 `investigation_evidence`；需要調查面板就重新匯出，檔案已存在則換新名稱。

`daily_usage` 的欄位契約如下：

| 欄位 | 語意 |
| --- | --- |
| `period` | `label=month_to_date`、`start=2026-09-01`、`end=2026-09-22` |
| `as_of`、`currency`、`unit`、`source` | 固定快照、`USD`、`AI credits` 與來源說明 |
| `granularity`、`coverage` | `daily_samples`；訓練視窗 2026-08-26～2026-09-22、`kind=sparse_training_samples` |
| `items` | 依日期排序的 22 筆日彙總；每筆只含 `date`、`net_quantity`、`net_amount` |
| `missing_dates` | 本次為 `[]`；只列缺少樣本的日期，不在 `items` 補零 |
| `limitations` | 來源與稀疏樣本的限制說明 |

本資料 `items` 的每日顯示值以兩位小數**各自**加總，credits 與 USD 都恰好對回 `cost_summary` 的 net 數字；每日檢核與跨維度小計的四捨五入容差要分開處理。日彙總沒有部門／模型維度，不能靠它臆造每日部門或模型 cross-filter；排行請讀 `department_ranking.ranking`、`model_breakdown.items`。Budget 與 seat 表讀各自的 section，不以 billing 或 forecast 代替。

| `investigation_evidence` 欄位 | 來源／用途 |
| --- | --- |
| `daily_comparison` | 完整 trend 回應，含兩期序列、summary、change 與來源／期間 |
| `teams` | AI Lab、Security、Platform Engineering 的 roster 回應陣列 |
| `workflows` | 同三隊的 workflow 回應陣列；每期全量 summary 與有界 sample runs |
| `options` | 完整 options 回應，含 options 陣列、remaining_period、combination 與假設 |

[Dashboard skill](../.github/skills/finops-dashboard/SKILL.md) 提供單一 HTML、Clawpilot 樣式與 [evidence 驗證規則](../.github/skills/finops-dashboard/references/evidence-contract.md)。學員檢視後手動開啟，以 File API 選取 mock JSON；不新增外連、CDN、server 或管理操作。缺少 `investigation_evidence` 時須重新匯出，不捏造兩期趨勢、成果或方案脈絡。

巢狀日期的驗證要分開：`investigation_evidence.daily_comparison.baseline.as_of` 為 **2026-08-22T23:59:59Z**，該 baseline 的 `period.start`／`period.end` 是 **2026-08-01／2026-08-22**；current daily comparison、roster 與 workflow 回應 envelope 的 `as_of` 則為 **2026-09-22T23:59:59Z**。Workflow 內部的 `baseline.period` 仍是 8 月範圍；不能要求所有巢狀 `as_of` 等於 September `cost_summary`。這不改變既有 MTD 快照，也不讓普通 `previous_month` 變成可用。

## 資料副本

同樣的 JSON/NDJSON fixtures 也放在 `starter/data/` 與 `solution/data/`，讓部署包自含資料。維護教材時要保持三份語意一致，由 solution 的 checkpoint tests 檢查；先跑 solution tests，再更新 starter checkpoints。不要只修改其中一份或把學員生成的 evidence 當作來源資料。

### 給教材維護者：檢查固定模擬資料

維護者可用 `scripts/generate_workshop_data.py --check` 檢查固定模擬資料與三份副本的一致性；這個模式只檢查，不改檔：

```powershell
python .\scripts\generate_workshop_data.py --check
```

bash 用 `python scripts/generate_workshop_data.py --check`。**學員直接使用現成資料，不需要執行生成器**；它不是 Lab 1 或選做 dashboard 的前置作業。

同時驗證獨立 August baseline、run ledger 依 date/user/model 對帳、業務 roster 與 matched pilot。Pilot 成本不加入 billing 總額；這些合成證據都不是 real adapter 的替代來源。
