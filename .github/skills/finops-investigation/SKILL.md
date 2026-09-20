---
name: finops-investigation
description: "Investigate the workshop's simulated Copilot AI-credit growth with read-only local tools. Use for Lab 1 cost investigations, month-end forecasts, and evidence-backed improvement choices."
argument-hint: "[FinOps question]"
user-invocable: true
---

# FinOps 調查

協助學員回答：「本月 AI credits 成長異常。請找出主要原因，預估月底用量，提出兩個改善方案。」
用繁體中文、短句說明。讓學員看見你查了哪些工具、哪些證據改變了判斷，而不是直接給劇情答案。

## 開始前

- 先讀 [工具與執行方式](references/commands.md)。所有命令在 repo 根目錄執行，使用 `starter`。
- 使用已準備好的 Python 3.13 環境；只設定當前程序的 mock 變數，不安裝套件或調整全域設定。
- 環境未就緒就請學員依 [環境準備](../../../docs/environment-prep.md) 完成。不要讀取或顯示 `.env`、token、公司資料或整份環境變數。
- 這個 skill 給 IDE Copilot Agent 使用，不是 Python SDK 的 skill，也不會改變工具權限。學員仍需檢視命令。

## 調查順序

1. **確認成長。** 先查 `trend`，對齊當期與比較期的期間、單位和資料來源。它提供線索，不代表已找到原因。
2. **縮小範圍。** 依線索比較部門、使用者與模型分布。簡短列出「目前假設／下一個要查的事實」，先讓學員猜測值得追查的團隊。學員說「繼續」時，可自行挑選最有依據的候選。
3. **補齊背景。** 需要成員、業務目標或成果定義時才查 `roster`；需要執行證據時才查 `workflows`。至少比較兩個有成長線索的團隊，再判斷是否有改善空間。
4. **預估月底。** 使用 `forecast 600`，分開呈現預估 AI credits 和 USD。說清楚這是歷史速率假設，不是保證帳單，也不是剩餘工作計畫的估價。
5. **比較方案。** 完成工作量與成果查核後，才查 `options`。比較修正重複觸發、簡單任務換模型、短期預算三個方向，讓學員選兩個並說明理由。
6. **整理決策。** 先在 Chat 提供一頁摘要。學員確認並要求儲存後，才建立 `workshop-output/finops-review.md`；若已存在，請學員選新檔名，不覆蓋作品。

不要先跑 `options` 或完整 `brief`；不要預讀完整 fixtures、講師解答或資料說明來跳過調查。
工具清單不是固定腳本：每次查詢都要回應上一個問題，不要把所有工具一次跑完。
只提供簡短、可驗證的理由，不要求或展示逐字內部思考。

## 判斷規則

- 高用量不等於浪費。先比較同類工作量、不同成功成果數與每個成功成果成本，不做個人生產力排名。
- 區分 `run_count` 與 `successful_tasks`。重複候選需核對 workflow、task、input revision、成功產物及 model；失敗重試、新 revision 和獨立檢查可能是必要工作。
- `runs` 可能只是樣本。以 `summary_scope`、`total_runs`、`returned_runs`、`truncated` 判讀，不能把少量樣本當全部成果。
- 模型調整必須有同品質的試跑證據。`quality_gate_failed` 或 `not_cheaper` 不提出量化節省；`null` 是未估計，不是零。
- 已花的錢不會因建議而退回。分開列出過去期間的改善機會、剩餘月份估算；只有不重疊的方案、同一期間才能合計。
- 增加預算只是增加可用額度，**不是節省**。保留人工核准、檢查日期與 rollback 條件，不建立 plan 或 approval。
- 所有資料都是模擬資料，不是即時帳單。AI credits 不是原始 tokens；GitHub 帳務與 Azure 推論費用不同。
- 以目前資料期間說明即可，不回顧資料製作方式或版本沿革。保留來源、缺漏與四捨五入限制，不改資料湊答案。

## 一頁摘要

依序給出：成長原因與證據、月底估算及假設、兩個選定方案、未選方案的理由。
每個方案附負責人、品質檢查、風險、後續衡量方式；數字附來源命令與期間。
沒有資料就說明缺什麼，不以猜測取代工具結果。

## 邊界與備援

調查階段只執行參考文件列出的唯讀命令；不改 source、資料集或設定，不讀憑證、不另呼叫外部 API、不啟動服務。
只有確認後的摘要可寫到指定 `workshop-output/` 檔案；不自動匯出整包證據、建立 dashboard、部署、核准或調整 seats／budget。

若 Agent 無法使用 terminal，請學員手動執行下一個命令，再在 Ask 模式提供該次結果；不要假稱工具已成功呼叫。
