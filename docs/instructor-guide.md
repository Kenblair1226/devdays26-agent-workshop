# 講師指南：40 人／90 分鐘

以 **本機 tools → 本機 Copilot SDK harness → 選配 Foundry** 為唯一主線。不要因 Azure 開通失敗犧牲前兩個 Labs，也不要把執行 solution 的示範當成學員已完成 hands-on。

## 開場 demo（0–8 分）

展示一次完整價值鏈：

1. 問：「本月至今哪個部門消耗最多 AI credits？」
2. 答案指出 AI Lab、2,400 credits、USD 26，以及 snapshot/歸屬限制。
3. 問：「主要哪些模型？如何節省 context/token，又不犧牲品質？」
4. 請 Agent 提出 seat 回收 plan，展示未核准不可執行。

強調三件事：**credits 不等於 tokens；觀察到高用量不等於浪費；hosting 與 model provider 是不同設定。** GitHub budget 不會限制 Azure BYOK inference 或 Hosted Agent compute 費用。

## Run of show

| 時間 | 講師任務 | TA／學員成果 |
| --- | --- | --- |
| 0–8 | 情境、完成品與安全邊界 | 知道今天不操作真實公司資料 |
| 8–15 | 啟動 starter baseline | Python3.13、cost=4760/44.88 |
| 15–19 | 解釋 billing 與 metrics | 知道各資料可／不可回答什麼 |
| 19–31 | Lab 1 實作 aggregation | 部門排行、Unallocated |
| 31–37 | 核對與 recovery | Checkpoint1 通過 |
| 37–42 | 展示 session、schema、handler | 理解 SDK 自管 runtime |
| 42–51 | Lab 2 接 tools 與 instructions | Checkpoint2 通過 |
| 51–63 | 問答與 console 人工核准 | `/plans`、`/approve`、`/audit` |
| 63–78 | Lab 3 或講師 demo | remote invocation 或明確標記的觀摩 |
| 78–86 | 治理／觀測延伸與 Q&A | 說得出 production 還缺什麼 |
| 86–90 | 收尾與清理 | 無遺留 token、host 程序 |

## 40 人現場操作

建議 3–4 位 TA 分區，收集「環境／程式／認證」三類問題；每個 lab 結束用舉手或簡單表單確認 checkpoint。不要收集 token、真實帳單或 screenshots of credentials。

| 決策點 | 行動 |
| --- | --- |
| 第 15 分仍卡安裝 | 使用課前備用機／pair programming；不分享帳密 |
| 第 34 分未完成 Lab 1 | `python scripts/checkpoint.py --lab 1`，保留學員 backup |
| 第 58 分未完成 Lab 2 | 還原 Lab 2 checkpoint，優先完成問答與人工核准 |
| 第 63 分 Foundry 未就緒或約三成學員落後 | 全場切換 Lab 3 demo |
| 部署等待超過 5 分鐘／廣泛 429 | 停止新的重試，使用既有 endpoint |

每個人原則上有自己的預建 Foundry environment；不是把全班連到同一個有寫入權限的 Agent。完成較快者可測試未知使用者、無 activity、不同期間或錯誤 payload；不要增加第四個 lab。

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

可追問：「Security credits 少於 Platform，但金額較高，為什麼不能只看排行？」「activity=null 是閒置還是未知？」「9 月 3 日 snapshot 能否回答 9 月 5 日此刻費用？」

所有金額／單價是教學假設。真實用量取自 billing API，不能用不同模型的原始 token 單價回推這份 fixture。

## 人工核准示範

使用 `python -m finops_agent chat`，讓模型建立 plan，再由你在 console 執行 `/approve PLAN_ID`。先輸入錯誤確認字串展示拒絕，再輸入完整 `APPROVE PLAN_ID`。模型無法呼叫這個 console command，也拿不到 confirmation token。

示範 seat 與 user budget 各一次。Seat removal 的 mock 結果是 `pending_cancellation`，不是「立即省下當月費用」。User budget 必須 hard stop；USD 0 可能直接封鎖，人工確認時要逐項解釋 payload。

`approval-demo --rehearse` 只用於自動彩排，永遠 mock、標記 simulated，不能用它證明真人核准。Approval 有期限、綁定 plan 內容，執行失敗不自動重試；真實遠端操作若回應遺失，要先確認遠端現況。

## Lab 3 demo 與觀測

課前依 [環境準備](environment-prep.md) 建立 40 個 learner environment 及講師備援。從完成版本執行同一份 `request.example.json`，比較本機／雲端 evidence，指認 `invocation_id` 與 `tool_calls`。`azd ai agent monitor` 顯示近期 console logs；`--follow` 才持續串流。

要看 App Insights 分散式 trace，必須課前配置該環境 exporter、權限與保留規則；不要把 console logging 宣稱為完整 token trace。Tool logs 只記名稱與結果類型，不記 keys、approval token 或整份企業報表。

Hosted 範例採**每次 invocation 獨立 mock state**，不提供跨使用者共享核准 API；學生不會透過 remote endpoint 寫真實 seats。若進一步產品化，需要登入／授權、可信部門來源、durable approval store、API concurrency 控制與完整 retention policy。

若全場 Foundry 不可用：展示課前錄影、request/response 和 source，明確標記「demo」，不要說現場部署成功。

## 真實 GitHub adapter：講師選配

只在受控的測試 organization 與講師設備操作。讀取時 `FINOPS_BACKEND=github`，CLI 另需 `--instructor`、`GITHUB_ORG` 與最小必要權限的 `GITHUB_ADMIN_TOKEN`；部門 mapping 經由 `FINOPS_DEPARTMENT_MAPPING` 提供。不得向學員分發這些值。

成本查詢目前只支援 **month_to_date**：organization totals 與 known-user breakdown 分開取得，尚未歸屬部分不能遺漏；provider 沒有 last-updated timestamp 時只能標記 retrieved-at，不能稱為 real-time。歷史/daily query 不支援時必須拒絕，而不是回傳零。

真實 writes 需要 `FINOPS_ALLOW_REAL_WRITES=true`、instructor CLI 路徑及人工確認。旗標本身不是核准；模型也不能提供「confirmed=true」替代人。檢查 organization、user、budget scope、USD amount、hard-stop 後才確認。課後關閉旗標、撤銷短期憑證，維護真實 audit 的存取權限，絕不提交到 repo。

可完全跳過真實 write demo；mock 仍完整涵蓋教學目標。

## 課前 release gate

從 solution 執行測試，再準備 starter。分別跑 starter baseline 與還原後的三個 checks；確認 recovery 不刪學生的編輯。使用 Python3.13 和 manifest 中宣告的 SDK 版本，不要只在其他版本上 import 一次就視為相容。

完整本機 transport 彩排可用 `FINOPS_TEST_RUNTIME=1` 執行 `solution/tests/test_sdk_roundtrip.py`：它使用真實 SDK/runtime、loopback fake model，不需雲端憑證；它證明 tool routing，不代表真實模型品質或 Azure identity 已驗證。課前仍需用活動帳號跑真正的 `ask`，以及在預建環境跑真正的 remote invoke。

## Cleanup

停止本機程序、退出 chat、撤銷活動 token。主辦方按私人環境清單回收 Azure resource，不讓學員自行對共用資源執行清除。保留課程 source 與 synthetic fixtures；不保留或提交帳密、正式 organization 資料、模型 session history 與 audit logs。
