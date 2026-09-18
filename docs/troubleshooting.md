# 疑難排解

先保住 Lab 1/2 的本機成果。Lab 3 資源或授權不可用時直接切換講師 demo，不用全場等待。

| 症狀 | 處理方式 |
| --- | --- |
| `No module named finops_agent` | 回 repo root，設定指向 `starter/src` 的絕對 `PYTHONPATH`；啟用 Python3.13 venv |
| `source` 找不到 `starter/.venv/bin/activate` | `.venv` 不在 Git 裡；先於 repo 根目錄執行 `python3.13 -m venv starter/.venv`，成功後再啟用並安裝 `starter/requirements.txt` |
| PowerShell 找不到 `Activate.ps1` | 先確認 Python 為 3.13，再執行 `python -m venv .\starter\.venv`；Windows 使用 `Scripts\Activate.ps1`，不是 bash 的 `bin/activate` |
| Lab 1 imports Copilot/Azure 失敗 | 確認執行目前版本的 `local_cli.py`；deterministic tools 不需先載入 SDK |
| Lab 1 的 `NotImplementedError` | 你可能使用舊版 starter；新版工具已全部提供，不應要求補 aggregation |
| `brief` 出現 `FileExistsError` | 保留既有輸出，改用 `--output workshop-output/lab1-evidence-v3.json`；Chat 附件與 dashboard 選檔也要使用新檔 |
| `brief is mock-only` | 設定 `FINOPS_BACKEND=mock`；分析包不能從 real backend 匯出 |
| Evidence 缺 `daily_usage`／仍是舊總額 | 使用更新的課程版本重新執行 `python -m finops_agent brief --output workshop-output/lab1-evidence-v3.json` 並載入新檔；舊檔也可能已有 `schema_version=2` 與 `2026-09-22T23:59:59Z`，不能只看日期或 schema。另核對全體 34,906.67 credits／USD 329.12；若新名字也已存在，再換另一個名字 |
| Copilot Chat 說無法看到分析包 | 在 VS Code Chat 附上生成的 JSON，不是只貼路徑；不要附 `.env` |
| 今天還沒到 9/22，JSON 已有後續日期 | 正常，以原始 2026-09-01～2026-09-03 三天基準乘上 22 / 3，重複三天模式至 9/21，再用各 user/model 三天平均補 9/22；這是教學用線性外推、預先模擬的資料，不是實測或經驗證的預測，也沒有平日／週末季節性模型 |
| 選做 dashboard 一打開沒有圖 | 未選檔前應顯示空白狀態說明；用頁面 File API 選檔鈕載入新版 mock evidence，不靠自動讀相對路徑 |
| 選做 dashboard 報 `file://`／CORS 錯誤 | 請 Copilot 移除 `fetch`／外連，改用 File API；不新增 server、npm、CDN 或 API key |
| Dashboard 讀損壞 JSON、缺欄位或加總不一致卻顯示零 | 應清除舊結果並明確顯示錯誤，不能捏造零；跨維度小計須先排除下列 0.01 四捨五入差異。舊 evidence 請重新產生新檔，不只檢查有無 `daily_usage` |
| Dashboard 趨勢不到 22 天／沒有到 9/22 | 先確認載入正確的新版 evidence；按 `daily_usage.items` 與 `missing_dates` 核對，有缺日須標未知並斷線，不能補零或插值 |
| Dashboard 選部門後每日曲線跟著改 | 日彙總沒有部門／模型維度；移除臆造的 cross-filter，排行排序與 credits／USD 切換不應改全體 34906.67／329.12 |
| Dashboard 把 0.01 差異當成資料毀損 | 原始資料先加總再顯示兩位小數；模型 credits 小計為 34906.66、部門 USD 小計為 329.13，但全體仍是 34906.67／329.12。跨維度採有界四捨五入容差，保留 `rounding_note`；gross credits 減 discount credits 也可能差 0.01。每日顯示值加總則應恰好對回全體 |
| Dashboard 將 org budget 已用改成 329.12 | Budget 必須讀自己的 snapshot：org 限額 600／已用 331.47／剩餘 268.53，carol 已用 102.67／限額 150／剩餘 47.33；run-rate USD 448.80 與情境餘額 270.88 另列 |
| Copilot Agent 提議安裝依賴、修改 source 或 `.env` | 拒絕越界操作；只允許 `workshop-output/finops-dashboard.html`（已有則新檔名），`starter/src/finops_agent/demo.html` 只作唯讀樣式參考，不複製 admin／API |
| Dashboard 把 JSON 文字當成 HTML／出現執行行為 | 請改成 `textContent`，不用 `innerHTML`；先檢視生成檔再手動開啟，不自動執行或上傳 |
| Chat 建議立刻回收 judy | 指出 activity=null 是未知；要求與 billing evidence 交叉比對、改成待確認事項 |
| Chat 把兩個方案合計成「月節省」 | 重申 A 是同一 snapshot 期間、B 是下月假設；時間與成本口徑不同不得加總 |
| Lab 2 的 `NotImplementedError` | 只補 `demo_connection.py` 的 factory；tools、instructions 與 UI 都已提供 |
| `demo` 頁面 403 | 使用該次啟動的正確 User/Admin link；把 user token 換成 admin view 不會取得管理權限 |
| 8098 已使用 | 加 `demo --port 8099`，再用新 console links |
| `Clear FINOPS_DATA_DIR` | Demo 只用打包的 synthetic data；清除該環境變數，不從其他資料目錄啟動 |
| 使用者申請到 220 後額度還是 150 | 正確，pending 不會修改 budget；已用 102.67／剩餘 47.33 不變，人核准後才是限額 220／剩餘 117.33 |
| 管理者核准後還是舊畫面 | 等待最多一個 3 秒輪詢週期；確認兩頁是同一個 server 的連結 |
| 無法提出另一筆提高限額申請 | 目前只允許一筆 pending；先完成管理者 review |
| 缺少 SDK 認證或模型 timeout | 修正認證後重試；若改用直接申請表單，標示不經模型，不能稱為 SDK 成功 |
| 已還原答案卻與測試介面不同 | 執行 `python scripts/checkpoint.py --lab all`；不要刪整個 starter 或混載兩個 package |
| `34906.67 / 329.12` 不一致 | 確認使用更新後的 synthetic data，三天基準按 22 / 3 外推，並重新產生、載入 evidence；不沿用舊總額，也不拿今日日期解讀固定 snapshot |
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
| Agent 回答沒有 evidence | 確認 instructions 和 tool schemas；看 `tool_calls`，不要只靠在 prompt 加「請正確回答」 |
| demo 使用者要求移除 seat 或自稱 admin | 正確地拒絕；使用者模型只有個人查詢與提高額度申請工具，seat 操作留作進階 CLI 範例 |
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

可執行現成 tools 與 demo 的直接申請／admin 核准；Lab 1 Copilot Chat 需 GitHub 登入，Lab 2 SDK 聊天需授權或 BYOK。由已登入的同學或講師示範時不要交換秘密。沒有活動 Foundry 環境就觀摩 Lab 3，不把本機 fake-model 彩排或 HTTP readiness 宣稱為雲端部署成功。

選做 dashboard 的 Agent 建檔沿用既有 Copilot 登入；已產生且檢視過的自含 HTML 可以在瀏覽器離線選取 mock JSON，沒有 server 或模型憑證。Agent 不可用就保留決策摘要、先進 Lab 2，不為了選做環節新增依賴或服務。
