# 疑難排解

先保住 Lab 1/2 的本機成果。Lab 3 資源或授權不可用時直接切換講師 demo，不用全場等待。

| 症狀 | 處理方式 |
| --- | --- |
| `No module named finops_agent` | 回 repo root，設定指向 `starter/src` 的絕對 `PYTHONPATH`；啟用 Python3.13 venv |
| Lab 1 imports Copilot/Azure 失敗 | 確認執行目前版本的 `local_cli.py`；deterministic tools 不需先載入 SDK |
| Lab 1 的 `NotImplementedError` | 這是預留 TODO，實作 aggregation，不是安裝問題 |
| Lab 2 check 缺少 tool names | 補齊 department ranking 與 plan 的 registrations，再測試 handler |
| 已還原答案卻與測試介面不同 | 執行 `python scripts/checkpoint.py --lab all`；不要刪整個 starter 或混載兩個 package |
| `4760 / 44.88` 不一致 | 確認使用 synthetic data、MTD 與固定 snapshot；不拿今日日期解讀範例 |
| `Unallocated` 不見或人數太多 | 保留 unknown users，對同部門使用者去重；先算總額，再截取 top-N |
| 無資料的期間回傳限制 | 正確行為；不要把 unavailable 改成零 |
| 第一次 `ask` 等候 runtime | 課前先 `python -m copilot download-runtime`；檢查 runtime download 網路，別另開 headless CLI |
| 缺 `COPILOT_GITHUB_TOKEN` | 依 [認證步驟](environment-prep.md#lab-2-模型認證) 設定個人 Copilot token；不使用 GitHub admin token |
| BYOK 沒生效／模型 404 | 明確選 `FINOPS_MODEL_PROVIDER=foundry-key`；確認 endpoint 與 deployment name，不只設定 key |
| Agent 回答沒有 evidence | 確認 instructions 和 tool schemas；看 `tool_calls`，不要只靠在 prompt 加「請正確回答」 |
| 直接要求移除 seat 卻被拒絕 | 正確行為；用同一個 `chat` 中的 `/plans`、`/approve PLAN_ID` 進行人確認 |
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
python .\scripts\checkpoint.py --lab 1
python .\scripts\checkpoint.py --lab 2
python -m pytest .\starter\checks -q
```

bash 將 `\` 改為 `/`。編輯先備份至 `.workshop-backups/`；source 與 `.env` 不會被整個刪除。若只完成 Lab 1，不要期待 Lab 2 check 自動通過。

## 無認證／無 Azure 時

可完成 tools、schema 與 mock human-confirmation 練習；模型 `ask` 需要授權或 BYOK。由已登入的同學或講師示範時不要交換秘密。沒有活動 Foundry 環境就觀摩 Lab 3，不把本機 fake-model 彩排或 HTTP readiness 宣稱為雲端部署成功。
