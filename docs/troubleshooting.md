# 疑難排解

先保住 Lab 1/2 的本機成果。Lab 3 資源或授權不可用時直接切換講師 demo，不用全場等待。

| 症狀 | 處理方式 |
| --- | --- |
| `No module named finops_agent` | 回 repo root，設定指向 `starter/src` 的絕對 `PYTHONPATH`；啟用 Python3.13 venv |
| `source` 找不到 `starter/.venv/bin/activate` | `.venv` 不在 Git 裡；先於 repo 根目錄執行 `python3.13 -m venv starter/.venv`，成功後再啟用並安裝 `starter/requirements.txt` |
| PowerShell 找不到 `Activate.ps1` | 先確認 Python 為 3.13，再執行 `python -m venv .\starter\.venv`；Windows 使用 `Scripts\Activate.ps1`，不是 bash 的 `bin/activate` |
| 找不到 `/finops-investigation` 或 `/finops-dashboard` | 在 VS Code 開啟 repo 根目錄，Chat 選 Agent；用 `/skills` 開 Configure Skills，確認 `chat.useAgentSkills` 已啟用（目前預設 true）。仍不可用時，附上 [調查 SKILL.md](../.github/skills/finops-investigation/SKILL.md) 或 [dashboard SKILL.md](../.github/skills/finops-dashboard/SKILL.md)，請 Agent 手動遵循；無須全域安裝或額外 extension |
| 把 skill 當成 SDK 工具或自動授權 | 這兩個是 VS Code IDE skills，不是 Python CLI 命令；SDK 維持 `enable_skills=False`、原有 roles／allowlist。Skill 不是權限沙箱，命令與 edits 仍須檢視 |
| Lab 1 imports Copilot/Azure 失敗 | 確認執行目前版本的 `local_cli.py`；deterministic tools 包括 `trend`／`roster`／`workflows`／`options` 不需載入 SDK，設好 `PYTHONPATH` 後可用 `python -S` |
| Lab 1 的 `NotImplementedError` | 你可能使用舊版 starter；新版工具已全部提供，不應要求補 aggregation |
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
| Copilot Agent 提議安裝依賴、修改 source 或 `.env` | 主線只准現成唯讀查詢，不編輯任何檔案。決策後的選做才允許 `workshop-output/finops-dashboard.html`（已有則新檔名）；`starter/src/finops_agent/demo.html` 僅唯讀樣式，不複製 admin／API。Prompt 不是 IDE 強制沙箱，使用者仍須拒絕越界 |
| Dashboard 把 JSON 文字當成 HTML／出現執行行為 | 請改成 `textContent`，不用 `innerHTML`；先檢視生成檔再手動開啟，不自動執行或上傳 |
| Dashboard 要加暫時預算按鈕 | 拒絕；proposal comparison 是唯讀，不提供 temporary_budget／approval API 或任何外部寫入。Lab 2 的 localhost 角色頁面是不同練習 |
| Chat 建議立刻回收 judy | 指出 activity=null 是未知；要求與 billing evidence 交叉比對、改成待確認事項 |
| Chat 因 AI Lab 用最多就建議全面削減 | 要求先查 roster／workflow：80 → 200 成功批次、每批 USD 0.953333／88 credits 穩定。量增加不證明浪費，仍需比對相同成功定義；不能因此保證所有 migration 都有效率 |
| Chat 把兩個方案合計成「月節省」 | A/B 的 9/1～9/22 反事實機會不退款；只有 9/23～9/30、假設成立且 cohorts 不重疊時才可合計 USD 9.63 + 5.65 = 15.28。不加歷史機會或 C 的 headroom，不保證精準 invoice |
| Chat 說 mini 可以省 40% tokens／credits | Pilot 20/20 對 20/20、USD 2 對 1.20 只支持該 simple-maintenance cohort 的貨幣比率；`estimated_credit_savings=null`。品質 gate 不過就沒有量化 savings 建議，不擴展到 migration |
| `estimate_status` 是 `quality_gate_failed`／`not_cheaper` 卻仍推薦固定節省 | 顯示 null 金額估算，不補零或沿用成功案例；只有 `conditional_pilot_estimate` 才提供條件式金額。A 的 `remaining_month_credit_savings=1026.67` 只屬於重複觸發方案，不能拿來推論 B 的 credits |
| Chat 說提高 budget 就省 USD 70 | 150 → 220 只增加 headroom，節省 USD 0。carol 剩餘 60 批次約 USD 61.60、個人合計 164.27 是工作計畫估算，與全組織 47,600 credits／448.80 歷史 run-rate 不同 |
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
| `azd ai agent monitor` 結束了 | 預設只抓近期 logs；需要持續串流才加 `--follow` |
| 真實用量與目前 seats 合計不相等 | 已移除使用者／歸屬／時間可能不同；以 organization totals 為準並檢視 residual，不丟掉差額 |

## 有備份的 recovery

從 repo root 執行：

```powershell
python .\scripts\checkpoint.py --lab 2
python -m pytest .\starter\checks -q
```

bash 將 `\` 改為 `/`。Recovery 的目標是 Lab 2 接線：編輯先備份至 `.workshop-backups/`，不刪 source、`.env` 或 `workshop-output/` 的 evidence、決策摘要與選做 dashboard。Lab 2 check 仍需完成 SDK 接線。Lab 1 分析或圖表卡住時先核對 evidence；可以跳過 dashboard，Checkpoint 1 仍以決策摘要為準。

## 無認證／無 Azure 時

可執行現成 tools 與 demo 的直接申請／admin 核准；Lab 1 Copilot Chat 需 GitHub 登入，Lab 2 SDK 聊天需授權或 BYOK。IDE Agent 不通可改人執行 CLI／Ask 逐次分析，CLI 本身不需 Azure credentials；不把這個 fallback 說成 SDK 成功。由已登入的同學或講師示範時不要交換秘密。沒有活動 Foundry 環境就觀摩 Lab 3，不把本機 fake-model 彩排或 HTTP readiness 宣稱為雲端部署成功。

選做 dashboard 的 Agent 建檔沿用既有 Copilot 登入；已產生且檢視過的自含 HTML 可以在瀏覽器離線選取 mock JSON，沒有 server 或模型憑證。Agent 不可用就保留決策摘要、先進 Lab 2，不為了選做環節新增依賴或服務。
