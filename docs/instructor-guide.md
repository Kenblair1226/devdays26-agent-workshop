# 講師指南：40 人工作坊

以 **現成 tools + Copilot Chat Agent 調查 → 本機 Copilot SDK harness → 選配 Foundry** 為唯一主線。Lab 1 的 hands-on 是看見證據逐步縮小範圍，而不是讀一包已整理好的答案；完成原因、forecast、兩方案決策後可選做 dashboard。不要因 Azure 開通失敗犧牲前兩個 Labs。

## 開場 demo

在 VS Code 開啟 repo 根目錄，Chat 選 **Agent 模式**，使用本專案的 [調查 skill](../.github/skills/finops-investigation/SKILL.md) 與已初始化 terminal。**不附整份 brief、不先跑 `options`、不把這份講師答案放進 context**。開場輸入：

> /finops-investigation 本月 AI credits 成長異常。請找出主要原因，預估月底用量，提出兩個改善方案

1. 先展示 `trend` 的每日 current／baseline、growth 與 department_changes，再讓 Agent 按線索查 user/model 分布。這些輸出不含 migration／重複 review 的原因。
2. 停在排行，問全場：「若只能砍一組，你會先砍誰？還缺什麼？」記下猜測，不把投票當執行授權。
3. 由學員選團隊，才呼叫 `roster '<部門>'`、`workflows '<部門>' --limit 6`。讓 Agent 短列「可驗證的假設／下一項需要的事實」，不要求私有推理過程，也不固定抄一整串命令。
4. 要求比較工作量、不同成功成果、同定義單位成本；如果最大團隊的成長被解釋了，再查另一個增長團隊。**取得這些證據後**才揭露下方反轉。
5. `forecast 600` 回歷史 run-rate；再用 `options` 比較 A／B／C，讓小組選兩個、為不選的方案辯護。最後才匯出 `brief --include-investigation`，可選做單一 HTML dashboard。

強調三件事：**credits 不等於 tokens；觀察到高用量不等於浪費；hosting 與 model provider 是不同設定。** GitHub budget 不會限制 Azure BYOK inference 或 Hosted Agent compute 費用。

IDE skill 不啟用 Python SDK skills，也不是權限沙箱；仍檢視命令，不准編輯 source、讀 credentials、安裝或外部 API。找不到 skill 時依 [準備與備案](environment-prep.md#lab-1-copilot-chat-準備) 處理；Agent 不可用可由人執行下一個唯讀命令、逐次貼給 Ask，不一次提供答案包。

開場展示的是 IDE Agent 的 **terminal tool history**：實際命令、回應與證據如何縮小範圍，不只展示最後答案的自述。選配 SDK／Hosted 示範可另讀 `tool_calls`，不要讓學員以為 Lab 1 要先啟動 SDK 或增加 CLI 旗標才能看到工具執行。

## 依成果推進的帶領流程

依學員完成狀態調整節奏，先守住 Lab 1 的分析成果與 Lab 2 的人工核准流程。Foundry 模型切換與 hosting 分別依環境就緒情況決定實作或示範。

| 階段 | 講師任務 | TA／學員成果 |
| --- | --- | --- |
| 開場 | 說明情境、完成品與安全邊界 | 知道今天不操作真實公司資料 |
| 環境確認 | 啟動 starter baseline | Python3.13、cost=34906.67/329.12 |
| Lab 1 | 趨勢 → 分布 → 按需 roster／workflow → forecast → 三選二；完成決策後才匯出，選做 dashboard | 一頁決策摘要：原因、工作量／成果、月底估算、2 行動與1 不選理由；來源、期間、owner 和品質 gate 齊備 |
| Lab 2 | 接上 harness，跑完 User 問答、加額申請與 Admin 核准 | pending 不改額度；approved 後 220／102.67／117.33，重新查詢並核對 audit |
| Lab 3（選配） | 切換 Foundry Model，再選配 Hosted 部署或講師 demo | 模型呼叫與 hosting 分別驗收；工具與核准規則不變，Azure inference 另計 |
| 延伸討論 | 模型選擇、治理與 Q&A | 釐清資料與權限限制，不增加第四個 Lab |
| 收尾 | 核對成果、清理 | 無遺留 token、host 程序 |

## 40 人現場操作

建議 3–4 位 TA 分區，收集「環境／程式／認證」三類問題；每個 lab 結束用舉手或簡單表單確認 checkpoint。不要收集 token、真實帳單或 screenshots of credentials。

| 決策點 | 行動 |
| --- | --- |
| 安裝或認證問題仍無法排除 | 使用課前備用機／pair programming；不分享帳密 |
| Lab 1 分析卡住 | 和 TA 確認當前假設與下一個唯讀命令；先核對成功定義、再完成兩個選擇和一個不選理由，不改成編碼題 |
| 選做 dashboard 卡住／Agent 模式不可用 | 保留決策摘要，先進 Lab 2；不為選做安裝平台、啟動 server 或犧牲核心成果 |
| Lab 2 接線卡住 | 還原 Lab 2 checkpoint，優先完成問答與人工核准 |
| Foundry 未就緒，或多數學員仍需完成本機核心流程 | 優先完成 Lab 1/2，Lab 3 改講師 demo |
| 部署受阻或出現廣泛 429 | 停止新的重試，使用既有 endpoint |

每個人原則上有自己的預建 Foundry environment；不是把全班連到同一個有寫入權限的 Agent。完成較快者可做 Lab 1 選做 dashboard，或測試未知使用者、無 activity、不同期間或錯誤 payload；不要增加第四個 lab。

## FinOps 分析體驗

把重點放在學員能回答哪些管理問題，以及如何用資料支持決策；不要改成架設額外平台的練習。

| 分析主題 | Lab 1 的具體任務 | 範圍限制 |
| --- | --- | --- |
| Daily growth / user-model leads | 兩期 22 日趨勢與成長貢獻，按線索深入部門 | 固定 synthetic snapshot，不宣稱 real-time 或季節性 |
| Workload / outcome evidence | 高總額是否伴隨更多成功工作？runs 增加是否帶來新成果？ | 同成功定義內比較，不排名個人生產力 |
| Workflow / model experiments | 核對重複 artifact 或簡單任務 pilot，區分假設和可確認原因 | 失敗重試、合規 review 與不同輸出不自動視為浪費 |
| UBB budget / business support | 以 carol 的剩餘 migration 工作討論 headroom | 個人計畫不是組織線性預測；headroom 不是節省 |
| Conditional option comparison | 三選二，列 owner、品質 gate、同期間效果與不選理由 | 無效益與導入成本就不聲稱已算出 ROI |
| Accounting caveats / 延伸 | 保留 Unallocated 660 credits；如需再查 ivan、judy activity | 不是主 ROI 或強制 seat removal，沒有 cost-center CRUD |
| Human-in-the-loop actions | Lab 1 只提議；Lab 2 User 提申請、Admin 點擊核准 | 不批次操作真實 organization |

不要要求學員安裝額外的 Docker / React / FastAPI 平台或交出 sync PAT。直接用本 repo 的工具、VS Code Copilot Chat 與 mock fixtures 展示分析成果。

## 基準答案與追問

### 揭露反轉：最大用量不等於最大浪費

這段是**講師答案**，等學員按需拿到 roster／workflow 才展示：

- **AI Lab（carol、dave）**在做 legacy platform migration。相同成功定義＝一批通過 regression checks：8 月參考期 **80** 個成功批次，9 月 **200**，工作量 +150%；net credits **7,040 → 17,600**、USD **76.27 → 190.67** 同增 150%。原始平均每成功批次 **USD 0.953333／88 credits** 兩期不變。這解釋高總額，不證明所有 production migration 都有效率，也不表示應替所有任務改用便宜模型。
- **Security（grace、heidi）**的 automated PR review 才是機會：baseline **30 runs／30 個不同成功 PR revision**，current **60 runs／仍 30 個成果**。其中 **30 個成功重複候選**具有相同 workflow、task_id、input_revision、result_digest **和 model**，先 `pull_request` 再 `push`；政策每 PR revision 只需一份自動產物。每成果 USD **0.882444 → 1.764889**。先由 owner 核對 dedup key、artifact 和必需 checks；失敗重試、變更 revision、不同模型輸出不自動算重複，人工／合規 checks 必須保留。
- **Platform Engineering 的 Alice／gpt-5.4 simple-maintenance cohort**提供另一個受限實驗：已觀察成本 **USD 38.87**。獨立 fictional matched pilot 的 20 個同類任務，原模型 **20/20 通過、USD 2**，mini **20/20 通過、USD 1.20**，貨幣成本比 **0.6**。它不是組織 billing，不證明每個任務可換模型，不能推論 token／credit 減少；品質 gate 失敗就不量化節省。

`workflows --limit 6` 的 `runs` 只是樣本；`current`／`baseline` 各自的 `summary`、`by_user`、`by_workflow` 涵蓋該團隊該期全部驗證過的 runs。帶學員核對 `returned_runs`、`total_runs`、`truncated`、`summary_scope`，不能加總六筆當成本。完整 ledger 按 date/user/model 對回 billing；沒有資料或未知團隊要明確失敗，不回零。

### 數字核對

| 問題 | 基準 |
| --- | --- |
| Snapshot／MTD | `2026-09-22T23:59:59Z`；2026-09-01～2026-09-22，含首尾 22 天 |
| 獨立 baseline／來源 | `usage-comparison.json`，2026-08-01～2026-08-22、`as_of=2026-08-22T23:59:59Z`，21,523.33 credits／USD 188.25；不是完整 8 月或普通 billing coverage |
| 兩期成長 | 13,383.33 credits（62.18%）／USD 140.87（74.83%），先算原始彙總再四捨五入 |
| 成長貢獻 | AI Lab +10,560 credits／USD 114.40；Security +2,823.33／26.47；其他群組不變 |
| Daily samples／coverage | 9 月每天有樣本、`missing_dates=[]`；訓練視窗 2026-08-26～2026-09-22，`sparse_training_samples`，8 月只提供 8/31 |
| MTD net 用量／金額 | 34,906.67 credits / USD 329.12 |
| MTD gross／discount | 35,933.33／1,026.67 credits；USD 339.68／10.56，原始精度下 gross − discount = net |
| AI Lab | 17,600 credits / USD 190.67 |
| Platform Engineering | 5,866.67 credits / USD 50.75 |
| Security | 5,646.67 credits / USD 52.95 |
| Mobile | 5,133.33 credits / USD 30.80 |
| Unallocated | 660 credits / USD 3.96 |
| gpt-5.4 | 18,920 net credits / USD 189.20 |
| gpt-5-mini | 8,653.33 net credits / USD 51.92 |
| claude-opus-5 | 7,333.33 net credits / USD 88.00 |
| 情境 budget=600 的 run-rate | 47,600 AI credits／USD 448.80；329.12 ÷ 22 × 30，`projected_over_budget=false`；不是工作量調整後的保證或已出帳金額 |
| AI Lab 占比 | 約 50.42% net credits、57.93% net amount |
| carol user budget | USD 150、已用 102.67、剩 47.33，使用率約 68.45%，hard stop |
| organization budget | USD 600、已用 331.47、剩 268.53，使用率約 55.25% |

可追問：「AI Lab 成本大幅增加，但每個成功批次不變，還要砍它嗎？」「Security 的 60 次 success 能算 60 個成果嗎？」「什麼情況下 retry 或另一個模型的 review 是必要的？」「如果今天還沒到 9/22，為什麼已有後續日期？」普通 billing `previous_month` 不支援；獨立比較用 `trend`，不能把 8/31 樣本當完整 baseline。

關鍵反例：ivan 的 seat activity 是 2026-08-31，距快照 22 天，但 MTD billing 仍有 660 credits；heidi 是 2026-09-13、距快照 9 天；judy 的 activity=null。合理結論應是先核實 telemetry、帳號狀態與業務需求，而不是「全部可回收」。`forecast 600` 算出的 600 − 329.12 = 270.88 是 scenario headroom，不能覆蓋 org budget 自己的 268.53；billing 329.12 也不能取代獨立的 consumed 331.47。

所有日期都是預先模擬，不是實測、經驗證的預測或季節性證據。Billing 的 8/31 carol 300 credits／USD 3 不計入 9 月；缺日未知，9 月每天有樣本也不代表真實帳務完整。28 天 user metrics 固定為 8/26～9/22，carol 的 `ai_credits_used` 為 13,066.67；`active_days` 與其他指標使用自己的觀察視窗，不與 MTD 混用。

原始資料保留小數精度，先加總再顯示兩位小數；部門／模型／使用者小計獨立四捨五入後可能差 0.01。模型 credits 顯示值相加為 34,906.66、部門金額為 USD 329.13，**不改全體 34,906.67／329.12**；gross credits 減 discount credits 的顯示值也會差 0.01。日彙總的顯示值則會恰好對回全體。讓學員分辨四捨五入差異與真正不一致，並保留 `rounding_note`。

成長與單位成本同樣用原始彙總算，不能用顯示值相減或相除去否定最後 0.01 差異。所有金額／單價都是教學假設，不能用正式模型 token 單價回推 fixture。

### 三選二討論：不規定唯一正解

| 選項 | 9/1～9/22 已觀察機會 | 9/23～9/30 剩餘 8 日的條件式影響 | 必須提出的 gate／owner |
| --- | --- | --- | --- |
| A `deduplicate_triggers` | USD 26.47／2,823.33 credits | 重複速率不變時 USD 9.63／1,026.67 AI credits，分欄 | Security workflow owner 確認每 PR revision 的必要 artifact；保留失敗重試／人工／合規 checks，衡量每成功成果成本與漏檢 |
| B `simple_task_model` | 僅 simple-maintenance 的 USD 15.55 | pilot 可代表後續且品質等同時 USD 5.65 | 平台 owner、相同品質 checks 與 rollback gate；追蹤 pass rate 和 per-success USD，`estimated_credit_savings=null` |
| C `temporary_budget` | 不是降成本措施 | carol 150 → 220，headroom +USD 70，節省 USD 0 | Migration owner + 人類管理者審 scope、hard stop、限額與 9/30 review／expiry；追蹤剩餘工作及完成批次 |

A 的 `remaining_month_credit_savings=1026.67` 是剩餘 8 日的條件式 credits 估計，不與 USD 相加。B 的 `estimate_status` 有三種：`conditional_pilot_estimate`、`quality_gate_failed`、`not_cheaper`；後兩者的 observed／remaining 金額估算為 null，不能沿用成功 pilot 的數字。B 的 `estimated_credit_savings=null` 在成功 pilot 下也不變，不可借用 A 的 credits 推論模型節省。

C 的依據：carol 當期 **100** 個成功批次、原始成本 **USD 102.666667**，9/30 前剩餘 **60** 批次，估計需 **USD 61.60**。加上個人 budget consumed 102.67 得 **164.27**，比目前 150 高 **14.27**；220 是有餘裕的提案，不是假裝全部 70 都一定花完。個人計畫估算與組織線性 forecast 不同。Budget fixture 已有 `expires_at` 9/30，但只是 mock metadata，沒有 production 自動回復／timer；由人安排 review。

- A+C 可以合理支持 migration 同時修正重複執行；A+B 可做條件式成本實驗。其他選擇也需對未處理風險提出交代，不按「有沒有選中講師答案」評分。
- A+B 為互不重疊 cohorts，**同一剩餘期間**才可合計 USD 15.28；過去機會不會退款，不加到未來估算，也不把 headroom 當成節省。不要承諾精準月底 invoice；若討論 448.80 − 15.28 = 433.52，必須明說其餘工作量不變且兩方案假設成立。
- 不要求降 migration 模型、削減大戶或回收 seat。問每組：「誰負責？品質何時算失敗？下次看哪個 measurable outcome？為何沒選第三個？」

## Lab 1 成果評量

請學員把經人工檢視的 Copilot 答案存為 `workshop-output/finops-review.md`。TA 抽查每人能說明下列項目；不以「pytest 成功」代替分析成果。

| 項目 | 合格條件 |
| --- | --- |
| 原因與 3 個發現 | 有來源命令／欄位、數字、兩期期間、as_of、單位與限制；區分成長驅動和可避免機會 |
| 工作量／成果查核 | 能解釋 AI Lab 單位成本穩定，以及 Security runs 與不同成功成果的差別 |
| 月底估算 | 47,600 credits／USD 448.80 是歷史 run-rate；個人剩餘工作另算，不混用 budget snapshot |
| 2 個優先行動 | 三選二，有理由、同期間估算、風險、owner／核准角色、品質 gate 與下次衡量指標 |
| 保留決策 | 第三個未選方案或暫不執行動作有證據理由，不能只是「AI 不確定」 |
| 交接 Lab 2 | 若選 C，current → proposed 與人審條件清楚；未選 C 也可用它演練核准，不改成必選答案 |

Unallocated 與 seat 是會計限制或完成主線後的追問，不是主 ROI。不拿 acceptance rate 代替 ROI，不把工作類型不同的 per-success 成本用來評分個人。

Copilot Chat 無法使用時，pair programming 或講師示範，不交換 token；仍讓學員檢視 evidence 並口頭提出決策，不要改回編碼題。

## Lab 1 選做 dashboard 帶領方式

先確認 Checkpoint 1 的決策摘要，再用 [dashboard skill](../.github/skills/finops-dashboard/SKILL.md) 建立一頁本機 dashboard；**不是新 Lab 或繳交要求**。長指令、Clawpilot 樣式與驗證規則都在 skill 及其 [evidence contract](../.github/skills/finops-dashboard/references/evidence-contract.md)，不必再貼整份 prompt。

1. **決策後**用 `brief --include-investigation` 匯出；輸出已存在就換新名稱。一般 `brief` 不預載業務脈絡，不為 dashboard 先洩漏答案。
2. 輸入 `/finops-dashboard 用 workshop-output/lab1-evidence.json 製作本機 dashboard`（若另存請換路徑）。檢視 edits，僅建立指定 HTML，不改 source／`.env`、不外連或加入管理功能；手動開啟後用 File API 選 JSON，不自動執行或上傳。
3. 用上方答案核對全體／每日加總、獨立 budget 與 run-rate；依 contract 檢查缺資料、0.01 rounding、兩期各自 snapshot、鍵盤與資料表。Sample runs 不取代全期 summary，headroom 不算 savings。

頁面尚未完成就先進 Lab 2，保留檔案讓學員稍後修正；不要把 dashboard 誤當成 Lab 2 的使用者／管理者介面或要部署的新服務。

## Lab 2 現場 demo 劇本

只讓學員補 `demo_connection.py` 的 `build_demo_harness()`，工具、instructions 與 UI 都預建。開 `python -m finops_agent demo`，把 User / Admin 兩頁並排；先讓學員看見流程，再依需要解釋 JSON schema。

1. User 問：「我目前花費多少？額度還剩多少？」卡片／回答為 carol 10,266.67 credits、USD 102.67；限額 150、剩餘 47.33。
2. User 問：「有什麼節省建議？」要求 evidence，不用額度降低取代效率建議。
3. User 說：「請提高到 USD 220，支持 9/30 前剩餘 60 個 migration 批次，估計還需 USD 61.60，請人 review。」這是學員帶入的計畫理由，不擴大模型資料 scope。顯示 pending；特別停一下，讓全場看到限額仍是 150、已用 102.67、剩餘 47.33。
4. Admin 檢視申請人、理由、user scope、hard stop、150 → 220 及 review／expiry，點「核准並套用 mock 額度」。+70 headroom 不是節省，mock expiry 不是自動回復機制。
5. User 頁面自動變成 approved、220／102.67／117.33，再問同一問題；既有花費不會因加額歸零。

提醒：User 頁面只看自己的資料；allowlist 只有 `get_my_costs`、`get_my_savings`、`request_budget_increase`，四個組織調查工具不加入。prompt 自稱 admin 沒有效果。Admin capability 不在 user responses／model tools；兩種角色的 endpoint 在後端檢查。這只是 localhost 的 role-play，不宣稱取代正式 SSO、授權與 durable request store。

模型不穩時，改用標示為「直接提交 mock 申請（不經模型）」的表單演示後半段，同時說明前半段 SDK 聊天未成功。重啟 process 可恢復初始額度和新的角色連結；不要做 blanket retries 造成多筆申請。

Seat 回收、通用 `chat` 的 `/approve`、`approval-demo` 都留作主線完成後的延伸討論或課後練習。**Lab 2 必做只有個人查詢、節省建議、提高限額與 admin approve。**

## Lab 3：Foundry Model 切換與選配部署

本次只加 Foundry Model；**不建立 Toolbox、政策檢索或新的 tracing integration**。課前依 [模型準備](environment-prep.md#lab-3-foundry-model-課前準備) 核對 endpoint、deployment name、inference 權限與 SDK 的 Responses/tool-calling 相容性，不能只在 portal 手動問一句就視為完整接通。

確認 Lab 2 核心流程完成、Foundry 模型與權限可用後，先停止 Lab 2 demo，切換 `FINOPS_MODEL_PROVIDER=foundry-identity` 並設定 `AZURE_OPENAI_ENDPOINT`、`MODEL_NAME` 再啟動；本機使用開發者身分，Hosted 才用 Managed Identity。已配 key 的備案則用 `foundry-key`，再加上 `AZURE_OPENAI_API_KEY`。GitHub Copilot 的 `COPILOT_MODEL` 不用改成 Azure deployment name。重新開啟兩個角色連結，提醒學員重啟會重設 mock 申請，不是模型替使用者還原預算。

用同一段問題重跑：查個人花費、節省建議、以剩餘 migration 計畫要求提高到 220、admin approve。數字應維持初始 150／102.67／47.33，pending 不變，核准後才是 220／102.67／117.33；三工具 scope 不變。比較措辭、evidence 引用、是否區分 headroom 與節省及延遲，**不要只因模型不同就宣稱較省**，更不要把合成 GitHub 帳務數字當成這次 Azure inference 的費用。

只換模型不需要部署 Hosted Agent。完成模型切換、預建 hosting 也就緒且學員進度允許時，再依 [選配 Hosted 部署](hosted-deployment.md) 操作，查看 `invocation_id` 與 `tool_calls`；`azd ai agent monitor` 只看近期 console logs，不宣稱完整 token trace。Tool logs 不記 keys、approval token 或整份企業報表。

Hosted 範例採**每次 invocation 獨立 mock state**，不提供 Lab 2 的瀏覽器頁面或跨使用者共享核准 API；學生不會透過 remote endpoint 寫真實 seats。若進一步產品化，需要登入／授權、可信部門來源、durable approval store、API concurrency 控制與完整 retention policy。

如果模型連線不通，停止 demo 後明確切回 `copilot`，恢復原本的 `COPILOT_MODEL` 和個人 token；或展示講師課前錄影。不要暗中 fallback 然後宣稱 Foundry 成功。若只有 hosting 不可用，保留已完成的模型 demo，hosting 部分改成觀摩即可。

## 真實 GitHub adapter：講師選配

只在受控的測試 organization 與講師設備操作。讀取時 `FINOPS_BACKEND=github`，CLI 另需 `--instructor`、`GITHUB_ORG` 與最小必要權限的 `GITHUB_ADMIN_TOKEN`；部門 mapping 經由 `FINOPS_DEPARTMENT_MAPPING` 提供。不得向學員分發這些值。

成本查詢目前只支援 **month_to_date**：organization totals 與 known-user breakdown 分開取得，尚未歸屬部分不能遺漏；provider 沒有 last-updated timestamp 時只能標記 retrieved-at，不能稱為 real-time。歷史/daily query 不支援時必須拒絕，而不是回傳零。

Comparison／roster／workflow／pilot 都是 mock 教學資料；real adapter 不會自動查到或捏造這些業務脈絡，四個調查工具只在一般 mock SDK toolset 註冊。它們也不提供真實 workflow 修正 API。

真實 writes 需要 `FINOPS_ALLOW_REAL_WRITES=true`、instructor CLI 路徑及人工確認。旗標本身不是核准；模型也不能提供「confirmed=true」替代人。檢查 organization、user、budget scope、USD amount、hard-stop 後才確認。課後關閉旗標、撤銷短期憑證，維護真實 audit 的存取權限，絕不提交到 repo。

可完全跳過真實 write demo；mock 仍完整涵蓋教學目標。

## 課前 release gate

從 solution 執行測試，再準備 starter。Lab 1 checks 在未編輯的 starter 應直接通過；還原 Lab 2 答案後，相關 checks 都要通過。確認一般 `brief` 不預載調查 context，`brief --include-investigation` 可產生 UTF-8 的 `schema_version=2` evidence、包含 `daily_usage`／`investigation_evidence` 且不覆蓋舊檔；recovery 不刪 `workshop-output/` 的分析摘要或選做 dashboard。使用 Python3.13 和 manifest 中宣告的 SDK 版本，不要只在其他版本上 import 一次就視為相容。

資料 release gate 核對固定 9/22 snapshot、9/1～9/22 的 22 個日期、`missing_dates=[]`，以及每日顯示值分別加總為 **34906.67 credits／329.12 USD**。跨維度小計用有界四捨五入容差，不把全體 USD 改成 329.13。另核對 sparse coverage、28 天 metrics 的獨立口徑、org **600／331.47／268.53** 與 carol **150／102.67／47.33 → 人核准後 220／102.67／117.33**。用 `--include-investigation` 重新匯出，已存在就換新名稱。文件回歸可跑 `python -m pytest solution/tests/test_workshop_docs.py -q -p no:cacheprovider`，檢查三個 Labs、project skills、核心 checkpoints、選做界線與無固定時程。

案例 gate：四個 fixture 副本一致；`trend` 不預載 roster／workflow／pilot；未知 scope、缺資料與不合法 limit 1..20 明確失敗。核對兩期 ledger 每 date/user/model、80 → 200 成果、30 → 60 runs／30 成果、pilot 不混入 billing，以及 A/B 同期估算、C headroom 不算 savings。不得讓 Lab 2 個人工具取得組織證據或 approve。

若講師要示範 dashboard，再手動驗證前述開檔／選檔、總數、錯誤狀態、鍵盤與表格替代；審查單一 HTML 無外連、憑證或管理操作。這是選做示範的檢查，**不是學員核心交付門檻**，也不需要把生成作品或額外主題資產提交進教材。

完整本機 transport 彩排可用 `FINOPS_TEST_RUNTIME=1` 執行 `solution/tests/test_sdk_roundtrip.py`：它使用真實 SDK/runtime、loopback fake model，不需雲端憑證；它證明 tool routing，不代表真實模型品質或 Azure identity 已驗證。課前仍需用活動帳號跑真正的 `ask`，以及在預建環境跑真正的 remote invoke。

## Cleanup

停止本機程序、退出 chat、撤銷活動 token。主辦方按私人環境清單回收 Azure resource，不讓學員自行對共用資源執行清除。保留課程 source 與 synthetic fixtures；不保留或提交帳密、正式 organization 資料、模型 session history 與 audit logs。
