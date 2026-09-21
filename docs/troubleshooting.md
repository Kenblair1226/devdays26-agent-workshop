# 疑難排解

先保住 Lab 1/2 的本機成果。Lab 2 的 Foundry model switch 可跳過；Lab 3 Hosted Agent 資源或授權不可用時直接切換講師 demo，不用全場等待。

| 症狀 | 處理方式 |
| --- | --- |
| `No module named finops_agent` | 回 repo root，設定指向 `starter/src` 的絕對 `PYTHONPATH`；啟用 Python3.13 venv |
| `source` 找不到 `starter/.venv/bin/activate` | `.venv` 不在 Git 裡；先於 repo 根目錄執行 `python3.13 -m venv starter/.venv`，成功後再啟用並安裝 `starter/requirements.txt` |
| PowerShell 找不到 `Activate.ps1` | 先確認 Python 為 3.13，再執行 `python -m venv .\starter\.venv`；Windows 使用 `Scripts\Activate.ps1`，不是 bash 的 `bin/activate` |
| 找不到 `/finops-investigation` 或 `/finops-dashboard` | 在 VS Code 開啟 repo 根目錄，Chat 選 Agent；用 `/skills` 開 Configure Skills，確認 `chat.useAgentSkills` 已啟用（目前預設 true）。仍不可用時，附上 [調查 SKILL.md](../.github/skills/finops-investigation/SKILL.md) 或 [dashboard SKILL.md](../.github/skills/finops-dashboard/SKILL.md)，請 Agent 手動遵循；無須全域安裝或額外 extension |
| 把 skill 當成 SDK 工具或自動授權 | 這兩個是 VS Code IDE skills，不是 Python CLI 命令；SDK 維持 `enable_skills=False`、原有 roles／allowlist。Skill 不是權限沙箱，命令與 edits 仍須檢視 |
| Lab 1 imports Copilot/Azure 失敗 | 確認執行目前版本的 `local_cli.py`；deterministic tools 包括 `trend`／`roster`／`workflows`／`options` 不需載入 SDK，設好 `PYTHONPATH` 後可用 `python -S` |
| Lab 1 的 `NotImplementedError` | Lab 1 工具已提供；請 TA 確認教材檔案完整，且 `PYTHONPATH` 指向 `starter/src`，不用另外實作 aggregation |
| Agent 新 terminal 找不到 package 或資料 | 回 repo root，啟用既有 venv，重設 `PYTHONPATH`、`FINOPS_BACKEND=mock`、`FINOPS_ALLOW_REAL_WRITES=false`；不讓調查 prompt 安裝、讀憑證或 provision |
| Agent／terminal tools 不可用 | 使用 Ask fallback：人手動執行下一個唯讀命令，只貼該次 JSON 結果，請模型給目前假設／下一項需要的事實；不一次附完整答案包 |
| Agent 想先讀整份 fixtures、教師答案或跑 `options` | 停止這一步，回到 `trend` → user/model 線索 → 按需 roster／workflow；先驗證工作量與成功成果，才能比較方案 |
| 缺 `usage-comparison.json`、`team-roster.json`、`workflow-runs.json` 或 `model-pilots.json` | 取得一致的新版教材／正確 `--data-dir`；由 TA 修正版本。不重新發明資料、不用真實 org 補、不把 unavailable 改為零；普通 `brief` 不驗證所有案例檔已備妥 |
| `roster`／`workflows` unknown department 或找不到該 scope | 用 `departments` 回傳的完整名稱與引號取代 `<部門>`，不要貼 placeholder 原文；未知或缺資料必須明確報錯，不回其他團隊或零 |
| Workflow limit 無效 | `--limit` 必須整數 1..20，例如 `--limit 6`；增加 sample 不等於增加全期統計的覆蓋 |
| `truncated=true`，以為只算了六筆 | `runs` 是展示樣本；每期 `summary`、`by_user`、`by_workflow` 涵蓋指定團隊所有驗證過的 runs，核對 `returned_runs`／`total_runs`／`summary_scope`，不要加總六筆代替全期 |
| 把成功執行／failed retry 都算成重複浪費 | 不同成功成果按 workflow／task／input_revision；重複候選還須同成功 result_digest 和 model。失敗重試、revision 變動或不同模型輸出不自動冗餘；workflow owner 確認每 revision 的自動產物政策，保留人工／合規 checks |
| 有 August 比較資料，`previous_month` 仍拒絕 | 正確；`usage-comparison.json` 是獨立 2026-08-01～2026-08-22 baseline，普通 sparse billing 不支援完整上月。比較請用 `trend` |
| `brief` 出現 `FileExistsError` | 保留既有輸出，換新檔名；決策後用 `brief --include-investigation` 匯出，Chat 附件與 dashboard 選檔使用同一新檔 |
| `brief is mock-only` | 設定 `FINOPS_BACKEND=mock`；分析包不能從 real backend 匯出 |
| Evidence 缺 `daily_usage`／`investigation_evidence` 或總額不符 | 決策後用 `python -m finops_agent --data-dir data brief --include-investigation --output workshop-output/lab1-evidence.json` 重新匯出；檔案已存在就換名。核對全體 34,906.67 credits／USD 329.12；一般 `brief` 不預載調查脈絡，缺資料不能靠模型猜 |
| Copilot Chat 說無法看到 evidence | 主線用已初始化 terminal 的逐次唯讀結果；Ask fallback 貼當次輸出。只有決策後選做 dashboard 才附新生成的 JSON，不是只貼路徑；不要附 `.env` |
| 今天還沒到 9/22，JSON 已有後續日期 | 正常；固定 2026-09-01～2026-09-22、snapshot `2026-09-22T23:59:59Z`，所有日期預先模擬，不是實測、即時用量或經驗證的預測 |
| 選做 dashboard 一打開沒有圖 | 未選檔前應顯示空白狀態說明；用頁面 File API 選檔鈕載入新版 mock evidence，不靠自動讀相對路徑 |
| 選做 dashboard 報 `file://`／CORS 錯誤 | 請 Copilot 移除 `fetch`／外連，改用 File API；不新增 server、npm、CDN 或 API key |
| Dashboard 讀損壞 JSON、缺欄位或加總不一致卻顯示零 | 依 [evidence contract](../.github/skills/finops-dashboard/references/evidence-contract.md) 清除舊結果並顯示錯誤，不捏造零；先排除 0.01 rounding。資料不完整就重新匯出 |
| Dashboard 趨勢不到 22 天／沒有到 9/22 | 先確認載入正確的新版 evidence；按 `daily_usage.items` 與 `missing_dates` 核對，有缺日須標未知並斷線，不能補零或插值 |
| Dashboard 選部門後每日曲線跟著改 | 日彙總沒有部門／模型維度；移除臆造的 cross-filter，排行排序與 credits／USD 切換不應改全體 34906.67／329.12 |
| Dashboard 把 0.01 差異當成資料毀損 | 原始資料先加總再顯示兩位小數；模型 credits 小計為 34906.66、部門 USD 小計為 329.13，但全體仍是 34906.67／329.12。跨維度採有界四捨五入容差，保留 `rounding_note`；gross credits 減 discount credits 也可能差 0.01。每日顯示值加總則應恰好對回全體 |
| Dashboard 調查面板缺資料或兩期 as_of 不同 | 要求用 `--include-investigation` 匯出新檔；不可從普通 brief 猜 migration／review／pilot。比較期 as_of 是 8/22，當期是 9/22，各 22 日，不必相同；增長差額由原始彙總算，顯示值相減可能差 0.01 |
| Dashboard 將 org budget 已用改成 329.12 | Budget 必須讀自己的 snapshot：org 限額 600／已用 331.47／剩餘 268.53，carol 已用 102.67／限額 150／剩餘 47.33；run-rate USD 448.80 與情境餘額 270.88 另列 |
| Copilot Agent 提議安裝依賴、修改 source 或 `.env` | Lab 1 調查階段只使用現成唯讀工具，不修改原始碼、資料集或設定。學員確認後，可儲存摘要至 `workshop-output/finops-review.md`；選做 dashboard 時才建立 `workshop-output/finops-dashboard.html`。檔案已存在請另取新名，不覆蓋作品。`starter/src/finops_agent/demo.html` 只可唯讀參考樣式，不複製 admin／API。Skill 不是 IDE 的強制權限沙箱，仍須檢視並拒絕越界操作 |
| Dashboard 把 JSON 文字當成 HTML／出現執行行為 | 請改成 `textContent`，不用 `innerHTML`；先檢視生成檔再手動開啟，不自動執行或上傳 |
| Dashboard 要加暫時預算按鈕 | 拒絕；proposal comparison 是唯讀，不提供 temporary_budget／approval API 或任何外部寫入。Lab 2 的 localhost 角色頁面是不同練習 |
| Chat 建議立刻回收 judy | 指出 activity=null 是未知；要求與 billing evidence 交叉比對、改成待確認事項 |
| Chat 因某團隊用最多就建議全面削減 | 請要求 Copilot 查詢該團隊的工作量、成功成果與單位成本，再判斷是否有改善空間。只比較相同成功定義的任務；高用量不等於浪費 |
| Chat 把兩個方案合計成「月節省」 | 只合計同一未來期間、假設成立且範圍互不重疊的方案估算。過去的改善機會不會退款，增加額度不算節省，也不能保證最終帳單 |
| Chat 用模型試跑金額推算 tokens／credits | 請核對試跑的任務範圍、通過率與金額。只有品質門檻通過時，才提供該範圍的條件式金額估算；`estimated_credit_savings=null` 表示未估計，不推算 tokens／credits，也不直接套用到其他任務 |
| `estimate_status` 是 `quality_gate_failed`／`not_cheaper` 卻仍推薦固定節省 | 顯示 null 金額估算，不補零或沿用成功案例；只有 `conditional_pilot_estimate` 才提供條件式金額。各方案的 `remaining_month_credit_savings` 只適用於自己的範圍與假設，不能拿來推論另一方案 |
| Chat 把提高預算當成節省 | 加額只是增加可用額度，沒有減少已用金額。請分開看工作計畫估算、帳務資料與預算餘額，再由管理者決定是否核准；不要把個人工作計畫與全組織歷史速率混為一談 |
| Lab 2 的 `NotImplementedError` | 只補 `demo_connection.py` 的 factory；tools、instructions 與 UI 都已提供 |
| `demo` 頁面 403 | 使用該次啟動的正確 User/Admin link；把 user token 換成 admin view 不會取得管理權限 |
| 8098 已使用 | 加 `demo --port 8099`，再用新 console links |
| `Clear FINOPS_DATA_DIR` | Demo 只用打包的 synthetic data；清除該環境變數，不從其他資料目錄啟動 |
| 使用者申請到 220 後額度還是 150 | 正確，pending 不會修改 budget；已用 102.67／剩餘 47.33 不變，人核准後才是限額 220／剩餘 117.33 |
| 認為 `expires_at` 9/30 會自動降回 150 | 它是 mock metadata，不是 production timer／自動回復；管理者仍須確認 scope、hard stop、限額及 review／expiry，安排人工後續 |
| 管理者核准後還是舊畫面 | 等待最多一個 3 秒輪詢週期；確認兩頁是同一個 server 的連結 |
| 無法提出另一筆提高限額申請 | 目前只允許一筆 pending；先完成管理者 review |
| 缺少 SDK 認證或模型 timeout | 修正認證後重試；若改用直接申請表單，標示不經模型，不能稱為 SDK 成功 |
| 已還原答案卻與測試介面不同 | 執行 `python scripts/checkpoint.py --lab all`；不要刪整個 starter 或混載兩個 package |
| `34906.67 / 329.12` 不一致 | 確認使用課程 synthetic data 與正確 `--data-dir`，重新匯出 evidence；不拿今日日期解讀固定 9/22 snapshot |
| `Unallocated` 不見或人數太多 | 保留 unknown users，對同部門使用者去重；先算總額，再截取 top-N |
| 無資料的期間回傳限制 | 正確行為；不要把 unavailable 改成零 |
| 第一次 `ask` 等候 runtime | 課前先 `python -m copilot download-runtime`；檢查 runtime download 網路，別另開 headless CLI |
| 缺 `COPILOT_GITHUB_TOKEN` | 依 [認證步驟](environment-prep.md#lab-2-模型認證) 設定個人 Copilot token；不使用 GitHub admin token |
| BYOK 沒生效／模型 404 | 選 `FINOPS_MODEL_PROVIDER=foundry-key`，完整設定 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_API_KEY`、`MODEL_NAME`；後者是 Azure deployment name |
| 改了 provider 但 demo 還是舊模型 | 停止並重啟程序，重新開啟 User/Admin 連結；正在跑的 session 不會讀入新的 shell 設定 |
| Foundry Model identity 401／403 | 主辦方確認課前開發者登入與 inference 權限；本機不是自動取得 Managed Identity，不要現場盲目新增 role |
| Foundry endpoint 404／base URL 錯誤 | `AZURE_OPENAI_ENDPOINT` 可填 resource/project 根 endpoint 或完整 `/openai/v1/` base URL；不能含 query、key、`/responses`、`/chat/completions` 或 Hosted invoke 路徑 |
| 出現舊 Foundry 設定遷移提醒 | 把 key 模式的舊三變數整組改成 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_API_KEY`、`MODEL_NAME`；GitHub Copilot 仍使用 `COPILOT_MODEL` |
| 重啟後額度回到 150、舊連結失效 | 正常，mock 狀態與 role capabilities 隨程序重設；carol 回到限額 150／已用 102.67／剩餘 47.33，不是更換模型自動修改 GitHub 帳務 |
| 模型通了但不能 Hosted deploy | 模型 inference 與 agent hosting 分開；可先完成模型比較，再觀摩部署 |
| 切回 Copilot 後仍然 model error | 停止程序，改回 `FINOPS_MODEL_PROVIDER=copilot`、帳號可用的 `COPILOT_MODEL` 與 token，再啟動 |
| Agent 回答沒有 evidence | Lab 1 看 IDE terminal tool history 的實際命令／回應；SDK／Hosted 示範才另看 `tool_calls`，不要只信回答自述或加一句「請正確回答」 |
| demo 使用者要求移除 seat 或自稱 admin | 正確地拒絕；使用者模型只有個人查詢與提高額度申請工具，seat 操作留作進階 CLI 範例 |
| Lab 2 模型沒有 `get_team_roster`／`get_workflow_evidence` | 正確；四個調查工具只供一般 mock SDK toolset，Lab 2 只有 `get_my_costs`／`get_my_savings`／`request_budget_increase`，不加入組織證據或 approve |
| Real backend 沒有合成案例工具 | 正確；不臆造真實 org 的 migration、workflow 或 pilot。案例維持 `FINOPS_BACKEND=mock`，不要為了取得情境改用 instructor credentials |
| `unknown plan` | `ask` 是一次性；改在同一個 `chat` 完成 planning / approval；重啟不保留 mock plans |
| approval 過期／token 不符 | 重新檢查計畫後核准；不要關閉 application policy |
| user budget 的 hard stop=false 被拒絕 | 正確；user-level budget 必須 hard stop |
| Foundry 503 | 檢查該 invocation 的 logs、模型設定與 identity；不能把 `/readiness` 200 當成模型可用 |
| Foundry 504 | 代表 request timeout，未回傳成功；先看 logs 再決定重試或 demo |
| Foundry 部署受阻／多數人 429 | 停止全班重試，使用既有 demo endpoint |
| 找不到 azd environment | 主辦方未完成個人 environment 綁定；不要在現場新建資源或反覆 init |
| `azd` 版本太舊 | 課前更新到 YAML 要求；本機 Lab 1/2 不受影響 |
| remote request body 無效 | 使用 `request.example.json` 與 `--protocol invocations -f`，不要傳裸字串或 UTF-16 JSON |
| Playground 顯示 `input must be 1-8000 characters` | 舊 Invocations handler 把格式錯誤也顯示為字數錯誤；不一定是問題太長。重新部署雙 protocol 版本，選新版本的 `responses` 並建立新聊天；JSON API 仍明確選 `invocations`，見 [Hosted 部署](hosted-deployment.md#使用-playgroundresponses) |
| Responses HTTP 200 但沒有成功回答 | 檢查 JSON 的 `status`／`error` 或 SSE 的 `response.failed`；這些是 protocol 內的失敗，不是成功答案。依 response ID 檢查對應 session logs |
| Playground 不記得上一題 | 本 workshop 的兩種 protocols 都使用每次 request 獨立的 harness／mock 狀態，不載入歷史；每題提供完整條件，不以聊天記錄當作跨 request memory |
| `azd ai agent monitor` 結束了 | 預設只抓近期 logs；需要持續串流才加 `--follow` |
| 真實用量與目前 seats 合計不相等 | 已移除使用者／歸屬／時間可能不同；以 organization totals 為準並檢視 residual，不丟掉差額 |

## 選配：本機 OpenTelemetry trace 檔

這是講師／維護者的本機診斷選項，不是 Lab 1/2 的必要步驟，也不新增 collector 或 Azure 服務。
在已完成 SDK 接線與認證的環境，於 `starter/.env` 設定：

```dotenv
FINOPS_OTEL_FILE=workshop-output/copilot-trace.jsonl
```

停止並重新啟動 `ask`、`chat` 或 `demo`，再送出一題會呼叫工具的問題。
相對路徑以**啟動程序的 working directory** 為準；需要固定位置時使用絕對路徑。
Harness 建立父目錄並檢查檔案可寫，runtime 以 JSON Lines 追加，不清空已有紀錄。
完整結果請在該次 SDK session 正常結束後查看；長時間開啟的 demo／chat 可能還有 spans 尚未結束。
設為空字串或移除變數後重啟，即關閉這個 runtime exporter。

可以在檔案中找：

| 欄位／span | 用途 |
| --- | --- |
| `type=span`、`gen_ai.operation.name=invoke_agent` | 本次 agent turn |
| `gen_ai.operation.name=chat` | 模型互動；通常有 model、input/output tokens，依模型實際提供的 usage 為準 |
| `gen_ai.operation.name=execute_tool` | 工具名稱、call ID 與執行狀態 |
| `traceId`、`spanId`、`parentSpanId` | 還原同一條 trace 的父子關係 |
| `startTime`、`endTime` | 耗時；格式是 `[seconds, nanoseconds]` |

檔案依 span 完成／匯出時間追加，不保證是開始時間順序，也可能包含 metrics 等非 span 紀錄。
`capture_content` 固定為 `false`：不開啟 prompt、回答或工具參數／結果的內容錄製。
仍可能包含模型／工具名稱、識別碼、endpoint metadata 等診斷資訊，不能當作完全匿名資料；
只在授權的本機除錯情境使用，不提交或任意上傳。建議路徑 `workshop-output/` 已被 Git 忽略。
這個設定不放寬 runtime 的 credential allowlist，也不把 `OTEL_*` 或 App Insights 設定整包傳給 runtime。

**本機 JSONL 不會自動顯示在 Foundry Traces。** Foundry host 的 Application Insights exporter
和 Copilot runtime 的 file／OTLP exporter 是不同的管線；connection string 不能直接當作 OTLP endpoint。
本選項不修改 Hosted 部署設定，也不宣稱完成雲端 telemetry 匯出。

### Hosted：批次匯出到 Foundry Traces

`azure.yaml` 的 hosted service 設定 `FINOPS_OTEL_EXPORTER=azure-monitor`；
本機 `.env.example` 預設留空，不影響 Azure-free Lab 1/2。
需要 project 已連結 Application Insights，並由平台注入
`APPLICATIONINSIGHTS_CONNECTION_STRING`。不要把 connection string 寫進 manifest 或 runtime 環境。
不能同時設定 `FINOPS_OTEL_FILE`：避免把本機累積檔案或舊 request 的 spans 上傳。
不合法的 exporter、缺少 connection string 或互斥設定會明確拒絕啟動 conversation。

每次 conversation 使用獨立暫存檔；Hosted 每個 request 就是一個 conversation。
runtime 關閉／flush 後才轉換及批次匯出，因此不是即時 token 串流，也不提供隱藏的模型推理內容。
保留原始 IDs、時間、status code、模型／工具與 token usage metadata，
沿用 host 的 service resource／可用 agent metadata，讓 spans 能接回同一 trace。
除了 `capture_content=false`，bridge 還會過濾 attributes 並丟棄 events 和錯誤描述，
不送 prompt、回答、工具參數／結果；名稱及識別碼仍不是匿名資料。
Native metrics records 不匯出；usage 來自 spans，不可當作帳單。

Exporter 在 worker thread 執行，重用 process 級 instance，連線／讀取 timeout 各 5 秒、
不自動重試；這不是整個 request 的嚴格 5 秒上限。
`APPLICATIONINSIGHTS_AUTH_MODE=entra` 與 host 一樣使用 system-assigned Managed Identity；
其餘使用 Azure Monitor SDK 的 connection string／標準 authentication 設定。
不新增 collector、不改 host 全域 tracing，不擴大 runtime credential allowlist。
匯出成功記錄 `Copilot runtime trace export succeeded; spans=...`；
失敗記錄 `Copilot runtime trace export failed`，buffer 損壞／超限記錄
`Copilot trace buffer rejected`，沒有完整 span 則記錄 warning。
診斷不包含原始 buffer 或 credentials；telemetry 失敗不偽裝成匯出成功，也不丟棄已完成的模型回答。
bridge 最多讀取 8 MiB／2048 spans，超限整批拒絕。
成功、失敗、timeout 或取消均透過 harness cleanup 清除暫存目錄；
中止程序可能來不及 flush／送達。取消時已開始的 network export 可能在 thread 繼續完成。
離線重送 storage 關閉，失敗不保證重送或送達。

只看到 host／HTTP spans 時，先檢查部署版本是否包含 bridge、開關與本次 session 的 exporter log。
再於 Portal 用同一 trace ID 檢查 `chat ...`／`execute_tool ...`，並留意 ingestion 延遲。
成功回答／成功匯出 log 不等於 Portal 可見性已驗證；查詢共用 Application Insights 需另取得授權。

### 無雲端憑證的維護者驗證

先依既有準備步驟安裝 solution 的依賴並下載 SDK-pinned runtime，再使用 Python 3.13。
從 repo root 執行：

```bash
FINOPS_TEST_RUNTIME=1 python -m pytest solution/tests/test_sdk_roundtrip.py -q
```

PowerShell：

```powershell
$env:FINOPS_TEST_RUNTIME = "1"
python -m pytest .\solution\tests\test_sdk_roundtrip.py -q
```

這組測試使用**真實 Copilot SDK/runtime + localhost 假模型 + mock 工具**，
檢查模型／工具 spans、trace context、usage 欄位及內容未錄製；JSONL 寫入 pytest 的暫存目錄。
同時測試本機檔案與 Hosted 暫存 bridge 兩種模式，雲端 exporter 由記憶體測試替身取代，
確認轉換後的原始 IDs／父子關係、span 數量及暫存檔清理，不連接 Application Insights。
假模型的 token usage 是測試值，不是 Azure／GitHub 真實用量或費用，也不算 Hosted 部署成功。

## 有備份的 recovery

從 repo root 執行：

```powershell
python .\scripts\checkpoint.py --lab 2
python -m pytest .\starter\checks -q
```

bash 將 `\` 改為 `/`。Recovery 的目標是 Lab 2 接線：編輯先備份至 `.workshop-backups/`，不刪 source、`.env` 或 `workshop-output/` 的 evidence、決策摘要與選做 dashboard。Lab 2 check 仍需完成 SDK 接線。Lab 1 分析或圖表卡住時先核對 evidence；可以跳過 dashboard，Checkpoint 1 仍以決策摘要為準。

## 無認證／無 Azure 時

可執行現成 tools 與 demo 的直接申請／admin 核准；Lab 1 Copilot Chat 需 GitHub 登入，Lab 2 SDK 聊天需授權或 BYOK。IDE Agent 不通可改人執行 CLI／Ask 逐次分析，CLI 本身不需 Azure credentials；不把這個 fallback 說成 SDK 成功。由已登入的同學或講師示範時不要交換秘密。沒有活動 Foundry model 就跳過 Lab 2 model switch；沒有 hosting 環境就觀摩 Lab 3，不把本機 fake-model 彩排或 HTTP readiness 宣稱為雲端部署成功。

選做 dashboard 的 Agent 建檔沿用既有 Copilot 登入；已產生且檢視過的自含 HTML 可以在瀏覽器離線選取 mock JSON，沒有 server 或模型憑證。Agent 不可用就保留決策摘要、先進 Lab 2，不為了選做環節新增依賴或服務。
