# 講師指南：40 人／90 分鐘

以 **現成 tools + Copilot Chat 分析 → 本機 Copilot SDK harness → 選配 Foundry** 為唯一主線。Lab 1 免寫程式，hands-on 是調查、追問、交叉比對與提出決策，不是完成 aggregation。不要因 Azure 開通失敗犧牲前兩個 Labs。

## 開場 demo（0–8 分）

先在 VS Code Copilot Chat 附上 mock evidence JSON，展示價值鏈，而不是先帶大家讀 Python：

1. 問：「本月至今哪個部門消耗最多 AI credits？」
2. 答案指出 AI Lab、2,400 credits、USD 26，以及 snapshot/歸屬限制。
3. 問：「主要哪些模型？如何節省 context/token，又不犧牲品質？」
4. 展示一頁「行動／假設／風險／核准角色」摘要，再說明 Lab 2 將此流程自動化且未核准不可執行。

強調三件事：**credits 不等於 tokens；觀察到高用量不等於浪費；hosting 與 model provider 是不同設定。** GitHub budget 不會限制 Azure BYOK inference 或 Hosted Agent compute 費用。

## Run of show

| 時間 | 講師任務 | TA／學員成果 |
| --- | --- | --- |
| 0–8 | 情境、完成品與安全邊界 | 知道今天不操作真實公司資料 |
| 8–15 | 啟動 starter baseline | Python3.13、cost=4760/44.88 |
| 15–18 | 產生分析包、附到 Copilot Chat | 不改程式，現成工具開箱可用 |
| 18–23 | 成本熱點與部門／模型 drilldown | 每個結論有欄位和計算式 |
| 23–29 | Budget / seat review | 區分過舊、未知、矛盾證據 |
| 29–33 | 比較節省方案 what-if | 假設、時間範圍與風險分開 |
| 33–37 | 一頁決策摘要 | 3 發現、2 行動、1 暫不執行 |
| 37–43 | 一個 harness factory 接線 | Checkpoint2 通過，不填多份 schema |
| 43–47 | 開啟 User / Admin 兩個頁面 | 角色分開、同一個 local demo |
| 47–52 | 使用者詢問花費與節省建議 | carol 已用 14、限額 20、剩餘 6 |
| 52–60 | 使用者提高額度申請、管理者核准 | pending 不改額度；approve 後 30／14／16 |
| 60–63 | 使用者再次詢問、核對 audit | 完整閉環而非只看「申請成功」 |
| 63–68 | 同一個 demo 切換到 Foundry Model | 模型來源變更，個人工具和核准規則不變 |
| 68–75 | 原有的選配 Hosted 部署／講師 demo | 模型呼叫與 agent hosting 分別驗收 |
| 75–78 | 比較前後結果與費用邊界 | 仍是 20 → 30／14／16，Azure inference 另計 |
| 78–86 | 模型選擇、治理與 Q&A | 不加入其他服務或第四個 Lab |
| 86–90 | 收尾與清理 | 無遺留 token、host 程序 |

## 40 人現場操作

建議 3–4 位 TA 分區，收集「環境／程式／認證」三類問題；每個 lab 結束用舉手或簡單表單確認 checkpoint。不要收集 token、真實帳單或 screenshots of credentials。

| 決策點 | 行動 |
| --- | --- |
| 第 15 分仍卡安裝 | 使用課前備用機／pair programming；不分享帳密 |
| 第 34 分未完成 Lab 1 | 不做 code recovery；縮成一個有依據的行動與一個保留決策，沿用同一分析包 |
| 第 58 分未完成 Lab 2 | 還原 Lab 2 checkpoint，優先完成問答與人工核准 |
| 第 63 分 Foundry 未就緒或約三成學員落後 | 全場切換 Lab 3 demo |
| 部署等待超過 5 分鐘／廣泛 429 | 停止新的重試，使用既有 endpoint |

每個人原則上有自己的預建 Foundry environment；不是把全班連到同一個有寫入權限的 Agent。完成較快者可測試未知使用者、無 activity、不同期間或錯誤 payload；不要增加第四個 lab。

## 22 分鐘的 FinOps 分析體驗

把重點放在學員能回答哪些管理問題，以及如何用資料支持決策；不要把這段時間用來架設額外平台。

| 分析主題 | Lab 1 的具體任務 | 範圍限制 |
| --- | --- | --- |
| Cost overview / per-user AI credits | 問誰／哪部門／哪模型用最多，追問兩種占比 | 固定 snapshot，不宣稱 real-time |
| Inactive-user / seat utilization review | ivan、judy 的 activity 與 billing evidence 交叉比對 | 不把 null 或過舊 telemetry 當刪除授權 |
| Cost Centers / Unassigned Users | 解釋 Unallocated 90，提出補歸屬資料的任務 | 沒有 cost-center CRUD 或跨企業 sync |
| UBB budget consumed / remaining | carol 與 org budget 是否合理、影響誰 | 依個別 scope 分開，非 unified hard cap |
| ROI / optimization / recommendation review | 比較兩個明列假設的方案，形成待核准建議 | 無效益與導入成本就不聲稱已算出 ROI |
| Human-in-the-loop actions | Lab 1 只提議；Lab 2 User 提申請、Admin 點擊核准 | 不批次操作真實 organization |

不要要求學員安裝額外的 Docker / React / FastAPI 平台或交出 sync PAT。直接用本 repo 的工具、VS Code Copilot Chat 與 mock fixtures 展示分析成果。

## 基準答案與追問

| 問題 | 基準 |
| --- | --- |
| MTD net 用量／金額 | 4,760 credits / USD 44.88 |
| AI Lab | 2,400 credits / USD 26 |
| Platform Engineering | 800 credits / USD 6.92 |
| Security | 770 credits / USD 7.22 |
| Mobile | 700 credits / USD 4.20 |
| Unallocated | 90 credits / USD 0.54 |
| gpt-5.4 | 2,580 net credits |
| 情境 budget=80 的 run-rate | 約 USD 448.80，不是已出帳金額 |
| AI Lab 占比 | 約 50.42% net credits、57.93% net amount |
| carol user budget | USD 20、已用 14、剩 6，使用率 70%，hard stop |
| organization budget | USD 80、已用 45.20、剩 34.80，使用率 56.5% |
| 方案 A（同一資料期間下降 10%） | USD 26 × 10% = USD 2.60，假設而非實績 |
| 方案 B（下個月回收 1 seat） | 教學假設 USD 19 × 1 = USD 19，下月／經另行確認後才成立 |

可追問：「Security credits 少於 Platform，但金額較高，為什麼不能只看排行？」「activity=null 是閒置還是未知？」「9 月 3 日 snapshot 能否回答 9 月 5 日此刻費用？」

關鍵反例：ivan 的 seat activity 過舊，但 MTD billing 仍有 90 credits；judy 的 activity=null。合理結論應是先核實 telemetry、帳號狀態與業務需求，而不是「全部可回收」。`forecast 80` 算出的 35.12 是 scenario headroom，不能覆蓋 org budget 自己的 34.80。

所有金額／單價是教學假設。方案 A、B 時間範圍不同，不可加總成「已節省 USD 21.60／月」。真實用量取自 billing API，不能用不同模型的原始 token 單價回推這份 fixture。

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

Copilot Chat 無法使用時，pair programming 或講師示範，不交換 token；仍讓學員檢視 evidence 並口頭提出決策。不要改回編碼題塞滿剩餘時間。

## Lab 2 現場 demo 劇本

只讓學員補 `demo_connection.py` 的 `build_demo_harness()`，工具、instructions 與 UI 都預建。開 `python -m finops_agent demo`，把 User / Admin 兩頁並排；不要先花十分鐘介紹 JSON schema。

1. User 問：「我目前花費多少？額度還剩多少？」卡片／回答為 carol 1,400 credits、USD 14；限額 20、剩餘 6。
2. User 問：「有什麼節省建議？」要求 evidence，不用額度降低取代效率建議。
3. User 說：「請提高到 USD 30，因為下週 migration 專案。」顯示 pending；特別停一下，讓全場看到限額仍是 20。
4. Admin 檢視申請人、理由、20 → 30，點「核准並套用 mock 額度」。
5. User 頁面自動變成 approved、30／14／16，再問同一問題；既有花費不會因加額歸零。

提醒：User 頁面只看自己的資料；prompt 自稱 admin 沒有效果。Admin capability 不在 user responses／model tools；兩種角色的 endpoint 在後端檢查。這只是 localhost 的 role-play，不宣稱取代正式 SSO、授權與 durable request store。

模型不穩時，改用標示為「直接提交 mock 申請（不經模型）」的表單演示後半段，同時說明前半段 SDK 聊天未成功。重啟 process 可恢復初始額度和新的角色連結；不要做 blanket retries 造成多筆申請。

Seat 回收、通用 `chat` 的 `/approve`、`approval-demo` 都留作課後或最後 8 分鐘的選配進階內容。**Lab 2 必做只有個人查詢、節省建議、提高限額與 admin approve。**

## Lab 3：Foundry Model 切換與選配部署

本次只加 Foundry Model；**不建立 Toolbox、政策檢索或新的 tracing integration**。課前依 [模型準備](environment-prep.md#lab-3-foundry-model-課前準備) 核對 endpoint、deployment name、inference 權限與 SDK 的 Responses/tool-calling 相容性，不能只在 portal 手動問一句就視為完整接通。

第 63 分鐘先停止 Lab 2 demo，切換 `FINOPS_MODEL_PROVIDER=foundry-identity` 並設定 `AZURE_OPENAI_ENDPOINT`、`MODEL_NAME` 再啟動；本機使用開發者身分，Hosted 才用 Managed Identity。已配 key 的備案則用 `foundry-key`，再加上 `AZURE_OPENAI_API_KEY`。GitHub Copilot 的 `COPILOT_MODEL` 不用改成 Azure deployment name。重新開啟兩個角色連結，提醒學員重啟會重設 mock 申請，不是模型替使用者還原預算。

用同一段問題重跑：查個人花費、節省建議、要求提高到 30、admin approve。數字應維持初始 20／14／6 → 核准後 30／14／16；可以比較措辭、evidence 引用與延遲，**不要只因模型不同就宣稱較省**，更不要把合成 GitHub 帳務數字當成這次 Azure inference 的費用。

只換模型不需要部署 Hosted Agent。剩餘時間與預建 hosting 就緒時，再從完成版本執行 `request.example.json`、查看 `invocation_id` 與 `tool_calls`；`azd ai agent monitor` 只看近期 console logs，不宣稱完整 token trace。Tool logs 不記 keys、approval token 或整份企業報表。

Hosted 範例採**每次 invocation 獨立 mock state**，不提供 Lab 2 的瀏覽器頁面或跨使用者共享核准 API；學生不會透過 remote endpoint 寫真實 seats。若進一步產品化，需要登入／授權、可信部門來源、durable approval store、API concurrency 控制與完整 retention policy。

如果模型連線不通，停止 demo 後明確切回 `copilot`，恢復原本的 `COPILOT_MODEL` 和個人 token；或展示講師課前錄影。不要暗中 fallback 然後宣稱 Foundry 成功。若只有 hosting 不可用，保留已完成的模型 demo，hosting 部分改成觀摩即可。

## 真實 GitHub adapter：講師選配

只在受控的測試 organization 與講師設備操作。讀取時 `FINOPS_BACKEND=github`，CLI 另需 `--instructor`、`GITHUB_ORG` 與最小必要權限的 `GITHUB_ADMIN_TOKEN`；部門 mapping 經由 `FINOPS_DEPARTMENT_MAPPING` 提供。不得向學員分發這些值。

成本查詢目前只支援 **month_to_date**：organization totals 與 known-user breakdown 分開取得，尚未歸屬部分不能遺漏；provider 沒有 last-updated timestamp 時只能標記 retrieved-at，不能稱為 real-time。歷史/daily query 不支援時必須拒絕，而不是回傳零。

真實 writes 需要 `FINOPS_ALLOW_REAL_WRITES=true`、instructor CLI 路徑及人工確認。旗標本身不是核准；模型也不能提供「confirmed=true」替代人。檢查 organization、user、budget scope、USD amount、hard-stop 後才確認。課後關閉旗標、撤銷短期憑證，維護真實 audit 的存取權限，絕不提交到 repo。

可完全跳過真實 write demo；mock 仍完整涵蓋教學目標。

## 課前 release gate

從 solution 執行測試，再準備 starter。Lab 1 checks 在未編輯的 starter 應直接通過；還原 Lab 2 答案後，三個 checks 都要通過。確認 `brief` 可產生 UTF-8 資料且不覆蓋舊檔、recovery 不刪學生分析摘要。使用 Python3.13 和 manifest 中宣告的 SDK 版本，不要只在其他版本上 import 一次就視為相容。

完整本機 transport 彩排可用 `FINOPS_TEST_RUNTIME=1` 執行 `solution/tests/test_sdk_roundtrip.py`：它使用真實 SDK/runtime、loopback fake model，不需雲端憑證；它證明 tool routing，不代表真實模型品質或 Azure identity 已驗證。課前仍需用活動帳號跑真正的 `ask`，以及在預建環境跑真正的 remote invoke。

## Cleanup

停止本機程序、退出 chat、撤銷活動 token。主辦方按私人環境清單回收 Azure resource，不讓學員自行對共用資源執行清除。保留課程 source 與 synthetic fixtures；不保留或提交帳密、正式 organization 資料、模型 session history 與 audit logs。
