# 講師指南：40 人工作坊

以 **現成 tools + Copilot Chat 分析 → 本機 Copilot SDK harness → 選配 Foundry** 為唯一主線。Lab 1 的 hands-on 是調查、追問、交叉比對與提出決策，完成後可選做由 Copilot 協助建立的網頁 dashboard。不要因 Azure 開通失敗犧牲前兩個 Labs。

## 開場 demo

先在 VS Code Copilot Chat 附上 mock evidence JSON，展示價值鏈，而不是先帶大家讀 Python：

1. 問：「本月至今哪個部門消耗最多 AI credits？」
2. 答案指出 AI Lab、17,600 credits、USD 190.67，以及 snapshot/歸屬限制。
3. 問：「主要哪些模型？如何節省 context/token，又不犧牲品質？」
4. 展示一頁「行動／假設／風險／核准角色」摘要。想延伸呈現方式可在 Lab 1 選做 dashboard，再說明 Lab 2 將查詢與申請流程自動化且未核准不可執行。

強調三件事：**credits 不等於 tokens；觀察到高用量不等於浪費；hosting 與 model provider 是不同設定。** GitHub budget 不會限制 Azure BYOK inference 或 Hosted Agent compute 費用。

## 依成果推進的帶領流程

依學員完成狀態調整節奏，先守住 Lab 1 的分析成果與 Lab 2 的人工核准流程。Foundry 模型切換與 hosting 分別依環境就緒情況決定實作或示範。

| 階段 | 講師任務 | TA／學員成果 |
| --- | --- | --- |
| 開場 | 說明情境、完成品與安全邊界 | 知道今天不操作真實公司資料 |
| 環境確認 | 啟動 starter baseline | Python3.13、cost=34906.67/329.12 |
| Lab 1 | 產生分析包，調查成本與 seats／budgets，比較 what-if；完成後可選做 dashboard | 一頁決策摘要：3 發現、2 行動、1 暫不執行；附來源、期間與假設，圖表不取代摘要 |
| Lab 2 | 接上 harness，跑完 User 問答、加額申請與 Admin 核准 | pending 不改額度；approved 後 220／102.67／117.33，重新查詢並核對 audit |
| Lab 3（選配） | 切換 Foundry Model，再選配 Hosted 部署或講師 demo | 模型呼叫與 hosting 分別驗收；工具與核准規則不變，Azure inference 另計 |
| 延伸討論 | 模型選擇、治理與 Q&A | 釐清資料與權限限制，不增加第四個 Lab |
| 收尾 | 核對成果、清理 | 無遺留 token、host 程序 |

## 40 人現場操作

建議 3–4 位 TA 分區，收集「環境／程式／認證」三類問題；每個 lab 結束用舉手或簡單表單確認 checkpoint。不要收集 token、真實帳單或 screenshots of credentials。

| 決策點 | 行動 |
| --- | --- |
| 安裝或認證問題仍無法排除 | 使用課前備用機／pair programming；不分享帳密 |
| Lab 1 分析卡住 | 縮成一個有依據的行動與一個保留決策，沿用同一分析包，和 TA 查核後接回主線 |
| 選做 dashboard 卡住／Agent 模式不可用 | 保留決策摘要，先進 Lab 2；不為選做安裝平台、啟動 server 或犧牲核心成果 |
| Lab 2 接線卡住 | 還原 Lab 2 checkpoint，優先完成問答與人工核准 |
| Foundry 未就緒，或多數學員仍需完成本機核心流程 | 優先完成 Lab 1/2，Lab 3 改講師 demo |
| 部署受阻或出現廣泛 429 | 停止新的重試，使用既有 endpoint |

每個人原則上有自己的預建 Foundry environment；不是把全班連到同一個有寫入權限的 Agent。完成較快者可做 Lab 1 選做 dashboard，或測試未知使用者、無 activity、不同期間或錯誤 payload；不要增加第四個 lab。

## FinOps 分析體驗

把重點放在學員能回答哪些管理問題，以及如何用資料支持決策；不要改成架設額外平台的練習。

| 分析主題 | Lab 1 的具體任務 | 範圍限制 |
| --- | --- | --- |
| Cost overview / per-user AI credits | 問誰／哪部門／哪模型用最多，追問兩種占比 | 固定 snapshot，不宣稱 real-time |
| Inactive-user / seat utilization review | ivan、judy 的 activity 與 billing evidence 交叉比對 | 不把 null 或過舊 telemetry 當刪除授權 |
| Cost Centers / Unassigned Users | 解釋 Unallocated 660 credits，提出補歸屬資料的任務 | 沒有 cost-center CRUD 或跨企業 sync |
| UBB budget consumed / remaining | carol 與 org budget 是否合理、影響誰 | 依個別 scope 分開，非 unified hard cap |
| ROI / optimization / recommendation review | 比較兩個明列假設的方案，形成待核准建議 | 無效益與導入成本就不聲稱已算出 ROI |
| Human-in-the-loop actions | Lab 1 只提議；Lab 2 User 提申請、Admin 點擊核准 | 不批次操作真實 organization |

不要要求學員安裝額外的 Docker / React / FastAPI 平台或交出 sync PAT。直接用本 repo 的工具、VS Code Copilot Chat 與 mock fixtures 展示分析成果。

## 基準答案與追問

| 問題 | 基準 |
| --- | --- |
| Snapshot／MTD | `2026-09-22T23:59:59Z`；2026-09-01～2026-09-22，含首尾 22 天 |
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
| 情境 budget=600 的 run-rate | 329.12 ÷ 22 × 30 = USD 448.80，`projected_over_budget=false`；不是已出帳金額 |
| AI Lab 占比 | 約 50.42% net credits、57.93% net amount |
| carol user budget | USD 150、已用 102.67、剩 47.33，使用率約 68.45%，hard stop |
| organization budget | USD 600、已用 331.47、剩 268.53，使用率約 55.25% |
| 方案 A（同一資料期間下降 10%） | 9/1～9/22 的 USD 190.67 × 10%，顯示 USD 19.07，假設而非實績 |
| 方案 B（下個月回收 1 seat） | 教學假設 USD 19 × 1 = USD 19，下月／經另行確認後才成立 |

可追問：「Security credits 少於 Platform，但金額較高，為什麼不能只看排行？」「activity=null 是閒置還是未知？」「如果今天還沒到 9/22，為什麼已經有後續日期？這能代表真實帳戶的未來用量嗎？」

關鍵反例：ivan 的 seat activity 是 2026-08-31，距快照 22 天，但 MTD billing 仍有 660 credits；heidi 是 2026-09-13、距快照 9 天；judy 的 activity=null。合理結論應是先核實 telemetry、帳號狀態與業務需求，而不是「全部可回收」。`forecast 600` 算出的 600 − 329.12 = 270.88 是 scenario headroom，不能覆蓋 org budget 自己的 268.53；billing 329.12 也不能取代獨立的 consumed 331.47。

原始 **2026-09-01～2026-09-03 的 4,760 credits／USD 44.88 乘上 22 / 3**，才是這次 22 天的合成 MTD，不是維持三天總量。來源三天保留，三天模式共 7 個週期到 9/21，再加 9/22 各 user/model 的三天平均。這是教學用**線性外推**，不是實測或經驗證的預測，沒有平日／週末季節性模型；未來日期也是預先模擬。8/31 的 carol 300 credits／USD 3 不變、不計入 9 月，其他缺日是未知；9 月每天有樣本，也不能推論真實帳務完整。

28 天 user metrics 固定為 8/26～9/22，`ai_credits_used` 是各使用者原始三天平均 × 28，carol 為 13,066.67；`active_days` 與其他行為計數仍是獨立合成的 28 天觀察，不等比例放大到超過視窗，也不與 MTD 混用。

原始資料保留小數精度，先加總再顯示兩位小數；部門／模型／使用者小計獨立四捨五入後可能差 0.01。模型 credits 顯示值相加為 34,906.66、部門金額為 USD 329.13，**不改全體 34,906.67／329.12**；gross credits 減 discount credits 的顯示值也會差 0.01。日彙總的顯示值則會恰好對回全體。讓學員分辨四捨五入差異與真正不一致，並保留 `rounding_note`。

所有金額／單價是教學假設。方案 A、B 時間範圍不同，不可加總成「已節省 USD 38.07／月」，也不能用不同模型的原始 token 單價回推這份 fixture。

## Lab 1 成果評量

請學員把經人工檢視的 Copilot 答案存為 `workshop-output/finops-review.md`。TA 抽查每人能說明下列項目；不以「pytest 成功」代替分析成果。

| 項目 | 合格條件 |
| --- | --- |
| 3 個發現 | 有 JSON section、數字、期間、單位與限制 |
| 跨表查核 | 能指出至少一個 activity 與 billing 不一致或無法判定的案例 |
| 2 個優先行動 | 有理由、假設、風險、owner／核准角色與下次衡量指標 |
| 保留決策 | 至少一個暫不執行的動作，理由不能只是「AI 不確定」 |
| 交接 Lab 2 | 候選 plan 清楚寫 current → proposed，仍是待核准狀態 |

範例可優先選：針對 AI Lab 做有限範圍的 context/model routing 實驗；或先補齊 Unallocated 的可信歸屬。合理答案不只有降 budget／移除 seat，也可以提高有業務理由的個人額度，並要求追蹤品質和消耗。

Copilot Chat 無法使用時，pair programming 或講師示範，不交換 token；仍讓學員檢視 evidence 並口頭提出決策，不要改回編碼題。

## Lab 1 選做 dashboard 帶領方式

先確認 Checkpoint 1 的決策摘要，再讓有意願的學員用 [學員手冊 prompt](student-lab.md) 建立一頁本機 dashboard；**不是新 Lab 或繳交要求**。示範時刻意說清楚：Ask 用來分析附件，Agent 會提議建立檔案，兩者都不能因為有 Copilot 登入就取得正式管理權限。

1. 重新執行 `brief`，用 `workshop-output/lab1-evidence-v3.json` 等新檔名保留舊成果，Chat 附件與網頁都切到新檔。舊檔也可能已有 `schema_version=2`、`daily_usage` 與 9/22 快照，日期和 schema 不能證明是更新後的數字。
2. 將編輯範圍限在 `workshop-output/finops-dashboard.html`，已有作品就換名字。學員先檢視 edits；不改 source／`.env`，`starter/src/finops_agent/demo.html` 僅作 Clawpilot 主題的唯讀參考，不複製其 admin／API。
3. 不自動執行或上傳生成結果。由學員手動開 HTML，先看空白狀態，再用 File API 選 JSON；不新增 npm、CDN、外部字型、server、API key、browser network calls 或 persistence。
4. 比對全體及每日加總 34906.67／329.12、AI Lab 17600／190.67、Unallocated 660／3.96，daily trend 有 22 個 9 月日期、9/22 結束；跨維度小計的 0.01 四捨五入差異不報錯。credits／USD 切換與排序不改總數，不從日彙總臆造部門或模型 cross-filter。
5. Budget 表獨立顯示 org 600／331.47／268.53 與 carol 150／102.67／47.33，seat 的 null 為未知；run-rate USD 448.80 與情境餘額 270.88 另列。沒有 seat／budget action buttons 或 approval tools。
6. 展示資料驗證的重要性：損壞 JSON、缺 `daily_usage`、欄位或超出四捨五入容差的加總不一致應顯示錯誤，不能全零或保留舊圖；缺日標未知並斷線。圖表要有表格替代，選檔與切換可用鍵盤，JSON 文字用 `textContent`，不用 `innerHTML`。

頁面尚未完成就先進 Lab 2，保留檔案讓學員稍後修正；不要把 dashboard 誤當成 Lab 2 的使用者／管理者介面或要部署的新服務。

## Lab 2 現場 demo 劇本

只讓學員補 `demo_connection.py` 的 `build_demo_harness()`，工具、instructions 與 UI 都預建。開 `python -m finops_agent demo`，把 User / Admin 兩頁並排；先讓學員看見流程，再依需要解釋 JSON schema。

1. User 問：「我目前花費多少？額度還剩多少？」卡片／回答為 carol 10,266.67 credits、USD 102.67；限額 150、剩餘 47.33。
2. User 問：「有什麼節省建議？」要求 evidence，不用額度降低取代效率建議。
3. User 說：「請提高到 USD 220，因為下週 migration 專案。」顯示 pending；特別停一下，讓全場看到限額仍是 150、已用 102.67、剩餘 47.33。
4. Admin 檢視申請人、理由、150 → 220，點「核准並套用 mock 額度」。
5. User 頁面自動變成 approved、220／102.67／117.33，再問同一問題；既有花費不會因加額歸零。

提醒：User 頁面只看自己的資料；prompt 自稱 admin 沒有效果。Admin capability 不在 user responses／model tools；兩種角色的 endpoint 在後端檢查。這只是 localhost 的 role-play，不宣稱取代正式 SSO、授權與 durable request store。

模型不穩時，改用標示為「直接提交 mock 申請（不經模型）」的表單演示後半段，同時說明前半段 SDK 聊天未成功。重啟 process 可恢復初始額度和新的角色連結；不要做 blanket retries 造成多筆申請。

Seat 回收、通用 `chat` 的 `/approve`、`approval-demo` 都留作主線完成後的延伸討論或課後練習。**Lab 2 必做只有個人查詢、節省建議、提高限額與 admin approve。**

## Lab 3：Foundry Model 切換與選配部署

本次只加 Foundry Model；**不建立 Toolbox、政策檢索或新的 tracing integration**。課前依 [模型準備](environment-prep.md#lab-3-foundry-model-課前準備) 核對 endpoint、deployment name、inference 權限與 SDK 的 Responses/tool-calling 相容性，不能只在 portal 手動問一句就視為完整接通。

確認 Lab 2 核心流程完成、Foundry 模型與權限可用後，先停止 Lab 2 demo，切換 `FINOPS_MODEL_PROVIDER=foundry-identity` 並設定 `AZURE_OPENAI_ENDPOINT`、`MODEL_NAME` 再啟動；本機使用開發者身分，Hosted 才用 Managed Identity。已配 key 的備案則用 `foundry-key`，再加上 `AZURE_OPENAI_API_KEY`。GitHub Copilot 的 `COPILOT_MODEL` 不用改成 Azure deployment name。重新開啟兩個角色連結，提醒學員重啟會重設 mock 申請，不是模型替使用者還原預算。

用同一段問題重跑：查個人花費、節省建議、要求提高到 220、admin approve。數字應維持初始 150／102.67／47.33，pending 不變，核准後才是 220／102.67／117.33；可以比較措辭、evidence 引用與延遲，**不要只因模型不同就宣稱較省**，更不要把合成 GitHub 帳務數字當成這次 Azure inference 的費用。

只換模型不需要部署 Hosted Agent。完成模型切換、預建 hosting 也就緒且學員進度允許時，再從完成版本執行 `request.example.json`、查看 `invocation_id` 與 `tool_calls`；`azd ai agent monitor` 只看近期 console logs，不宣稱完整 token trace。Tool logs 不記 keys、approval token 或整份企業報表。

Hosted 範例採**每次 invocation 獨立 mock state**，不提供 Lab 2 的瀏覽器頁面或跨使用者共享核准 API；學生不會透過 remote endpoint 寫真實 seats。若進一步產品化，需要登入／授權、可信部門來源、durable approval store、API concurrency 控制與完整 retention policy。

如果模型連線不通，停止 demo 後明確切回 `copilot`，恢復原本的 `COPILOT_MODEL` 和個人 token；或展示講師課前錄影。不要暗中 fallback 然後宣稱 Foundry 成功。若只有 hosting 不可用，保留已完成的模型 demo，hosting 部分改成觀摩即可。

## 真實 GitHub adapter：講師選配

只在受控的測試 organization 與講師設備操作。讀取時 `FINOPS_BACKEND=github`，CLI 另需 `--instructor`、`GITHUB_ORG` 與最小必要權限的 `GITHUB_ADMIN_TOKEN`；部門 mapping 經由 `FINOPS_DEPARTMENT_MAPPING` 提供。不得向學員分發這些值。

成本查詢目前只支援 **month_to_date**：organization totals 與 known-user breakdown 分開取得，尚未歸屬部分不能遺漏；provider 沒有 last-updated timestamp 時只能標記 retrieved-at，不能稱為 real-time。歷史/daily query 不支援時必須拒絕，而不是回傳零。

真實 writes 需要 `FINOPS_ALLOW_REAL_WRITES=true`、instructor CLI 路徑及人工確認。旗標本身不是核准；模型也不能提供「confirmed=true」替代人。檢查 organization、user、budget scope、USD amount、hard-stop 後才確認。課後關閉旗標、撤銷短期憑證，維護真實 audit 的存取權限，絕不提交到 repo。

可完全跳過真實 write demo；mock 仍完整涵蓋教學目標。

## 課前 release gate

從 solution 執行測試，再準備 starter。Lab 1 checks 在未編輯的 starter 應直接通過；還原 Lab 2 答案後，三個 checks 都要通過。確認 `brief` 可產生 UTF-8 的 `schema_version=2` evidence、包含 `daily_usage` 且不覆蓋舊檔；recovery 不刪 `workshop-output/` 的分析摘要或選做 dashboard。使用 Python3.13 和 manifest 中宣告的 SDK 版本，不要只在其他版本上 import 一次就視為相容。

資料 release gate 要核對原始三天來源列未變、用量與金額按 22 / 3 外推、固定 9/22 snapshot、9/1～9/22 的 22 個日期、`missing_dates=[]`，以及每日顯示值分別加總為 **34906.67 credits／329.12 USD**。跨部門／模型／使用者小計用有界四捨五入容差；不把全體 USD 改成 329.13。另核對 sparse coverage、8/31 不計入 9 月、28 天 metrics 的獨立口徑、org **600／331.47／268.53** 與 carol **150／102.67／47.33 → 人核准後 220／102.67／117.33**。必須新產生 evidence 再載入，不能以舊檔也有 schema 2／9/22 日期就放行。文件回歸可跑 `python -m pytest solution/tests/test_workshop_docs.py -q -p no:cacheprovider`，檢查三個 Labs、核心 checkpoints、22 / 3 基準、選做界線與無固定時程。

若講師要示範 dashboard，再手動驗證前述開檔／選檔、總數、錯誤狀態、鍵盤與表格替代；審查單一 HTML 無外連、憑證或管理操作。這是選做示範的檢查，**不是學員核心交付門檻**，也不需要把生成作品或額外主題資產提交進教材。

完整本機 transport 彩排可用 `FINOPS_TEST_RUNTIME=1` 執行 `solution/tests/test_sdk_roundtrip.py`：它使用真實 SDK/runtime、loopback fake model，不需雲端憑證；它證明 tool routing，不代表真實模型品質或 Azure identity 已驗證。課前仍需用活動帳號跑真正的 `ask`，以及在預建環境跑真正的 remote invoke。

## Cleanup

停止本機程序、退出 chat、撤銷活動 token。主辦方按私人環境清單回收 Azure resource，不讓學員自行對共用資源執行清除。保留課程 source 與 synthetic fixtures；不保留或提交帳密、正式 organization 資料、模型 session history 與 audit logs。
