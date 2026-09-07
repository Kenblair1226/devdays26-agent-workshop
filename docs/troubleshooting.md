# 疑難排解

先保住 Lab 1/2 的本機成果。Lab 3 資源或授權不可用時直接切換講師 demo，不用全場等待。

| 症狀 | 處理方式 |
| --- | --- |
| `No module named finops_agent` | 回 repo root，設定指向 `starter/src` 的絕對 `PYTHONPATH`；啟用 Python3.13 venv |
| Lab 1 imports Copilot/Azure 失敗 | 確認執行目前版本的 `local_cli.py`；deterministic tools 不需先載入 SDK |
| Lab 1 的 `NotImplementedError` | 你可能使用舊版 starter；新版工具已全部提供，不應要求補 aggregation |
| `brief` 出現 `FileExistsError` | 保留既有輸出，改用 `--output workshop-output/lab1-evidence-v2.json` |
| `brief is mock-only` | 設定 `FINOPS_BACKEND=mock`；分析包不能從 real backend 匯出 |
| Copilot Chat 說無法看到分析包 | 在 VS Code Chat 附上生成的 JSON，不是只貼路徑；不要附 `.env` |
| Chat 建議立刻回收 judy | 指出 activity=null 是未知；要求與 billing evidence 交叉比對、改成待確認事項 |
| Chat 把兩個方案合計成「月節省」 | 重申 A 是同一 snapshot 期間、B 是下月假設；時間與成本口徑不同不得加總 |
| Lab 2 的 `NotImplementedError` | 只補 `demo_connection.py` 的 factory；tools、instructions 與 UI 都已提供 |
| `demo` 頁面 403 | 使用該次啟動的正確 User/Admin link；把 user token 換成 admin view 不會取得管理權限 |
| 8098 已使用 | 加 `demo --port 8099`，再用新 console links |
| `Clear FINOPS_DATA_DIR` | Demo 只用打包的 synthetic data；清除該環境變數，不從其他資料目錄啟動 |
| 使用者申請後額度還是 20 | 正確，pending 不會修改 budget；等待管理者核准 |
| 管理者核准後還是舊畫面 | 等待最多一個 3 秒輪詢週期；確認兩頁是同一個 server 的連結 |
| 無法提出另一筆提高限額申請 | 目前只允許一筆 pending；先完成管理者 review |
| 缺少 SDK 認證或模型 timeout | 修正認證後重試；若改用直接申請表單，標示不經模型，不能稱為 SDK 成功 |
| 已還原答案卻與測試介面不同 | 執行 `python scripts/checkpoint.py --lab all`；不要刪整個 starter 或混載兩個 package |
| `4760 / 44.88` 不一致 | 確認使用 synthetic data、MTD 與固定 snapshot；不拿今日日期解讀範例 |
| `Unallocated` 不見或人數太多 | 保留 unknown users，對同部門使用者去重；先算總額，再截取 top-N |
| 無資料的期間回傳限制 | 正確行為；不要把 unavailable 改成零 |
| 第一次 `ask` 等候 runtime | 課前先 `python -m copilot download-runtime`；檢查 runtime download 網路，別另開 headless CLI |
| 缺 `COPILOT_GITHUB_TOKEN` | 依 [認證步驟](environment-prep.md#lab-2-模型認證) 設定個人 Copilot token；不使用 GitHub admin token |
| BYOK 沒生效／模型 404 | 明確選 `FINOPS_MODEL_PROVIDER=foundry-key`；確認 endpoint 與 deployment name，不只設定 key |
| Agent 回答沒有 evidence | 確認 instructions 和 tool schemas；看 `tool_calls`，不要只靠在 prompt 加「請正確回答」 |
| demo 使用者要求移除 seat 或自稱 admin | 正確地拒絕；使用者模型只有個人查詢與提高額度申請工具，seat 操作留作進階 CLI 範例 |
| `unknown plan` | `ask` 是一次性；改在同一個 `chat` 完成 planning / approval；重啟不保留 mock plans |
| approval 過期／token 不符 | 重新檢查計畫後核准；不要關閉 application policy |
| user budget 的 hard stop=false 被拒絕 | 正確；user-level budget 必須 hard stop |
| Foundry 503 | 檢查該 invocation 的 logs、模型設定與 identity；不能把 `/readiness` 200 當成模型可用 |
| Foundry 504 | 代表 request timeout，未回傳成功；先看 logs 再決定重試或 demo |
| Foundry 部署超過 5 分鐘／多數人 429 | 停止全班重試，使用既有 demo endpoint |
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

bash 將 `\` 改為 `/`。Lab 1 免寫程式，不需 restore；Lab 2 編輯先備份至 `.workshop-backups/`，不刪 source、`.env` 或 Lab 1 的決策摘要。Lab 2 check 仍需完成 SDK 接線。

## 無認證／無 Azure 時

可執行現成 tools 與 demo 的直接申請／admin 核准；Lab 1 Copilot Chat 需 GitHub 登入，Lab 2 SDK 聊天需授權或 BYOK。由已登入的同學或講師示範時不要交換秘密。沒有活動 Foundry 環境就觀摩 Lab 3，不把本機 fake-model 彩排或 HTTP readiness 宣稱為雲端部署成功。
