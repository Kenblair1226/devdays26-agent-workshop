---
name: finops-dashboard
description: "Create or repair the optional Lab 1 local FinOps dashboard from exported synthetic evidence. Use when the learner explicitly requests a single-file HTML dashboard after the investigation."
argument-hint: "[evidence JSON path] [optional HTML output path]"
user-invocable: true
disable-model-invocation: true
---

# FinOps Dashboard

把學員完成調查後匯出的 mock evidence，做成一頁易讀的繁體中文 dashboard。
這是選做項目，不是新的 Lab，也不是預算管理介面。

## 開始前先確認

1. 使用者已完成調查與選案，並提供 evidence 路徑或附件。預設為 `workshop-output/lab1-evidence.json`。
2. 讀取 [資料與驗證規則](references/evidence-contract.md)，再查看實際 JSON；不猜欄位或把驗收數字硬編成畫面資料。
3. 預設輸出為 `workshop-output/finops-dashboard.html`。只可建立這一個指定檔案；已有作品就請使用者選新名字，不覆蓋原檔。只有使用者明確要求修正既有作品時，才編輯那個 HTML。
4. 若缺資料或調查 section，請使用者在終端以 `brief --include-investigation` 匯出新檔；不在這個 skill 裡執行命令或補寫案例答案。

## 實作範圍

- 單一自含 HTML/CSS/JavaScript，以 vanilla SVG/CSS 畫圖；不需要安裝或 build。
- 使用 File API 選檔後讀入 JSON，讓 `file://` 直接開啟可用；不要 `fetch`、API、SDK、backend、server、CDN、外部字型或任何網路呼叫。
- 不讀 `.env`、keys、token 或真實組織資料；不改 source、JSON 資料集或設定。
- 不使用 localStorage、cookie 或其他 persistence。重整頁面後重新選檔。
- 不提供 seat／budget／temporary_budget 變更按鈕、approval tools、登入或角色切換。
- 不執行命令，不自動開啟、執行或上傳生成結果；先讓使用者檢視檔案差異。

## 畫面與操作

- 清楚標示「合成教學資料」、目前資料期間、來源及限制；不描述資料版本沿革。
- 呈現總用量、每日趨勢、部門／模型排行，金額與 AI credits 分開。
- 將執行次數、成功成果及每成果成本放在一起，讓讀者看見工作量背景；只比較同類任務。
- 三方案表分開呈現歷史機會、剩餘期估算及增加的額度；增加預算不是節省。
- 預算、帳務、月底估算各自成區，不互相覆蓋。
- 初始只顯示清楚的選檔說明，不顯示假數字。資料不合法時清除舊內容，用 `role=alert` 說明原因；不可補成零。
- JSON 文字一律用 `textContent` 呈現，不使用 `innerHTML` 或當成程式執行。
- 選檔、排序、切換可用鍵盤操作，焦點清楚；圖表須有單位及可閱讀的資料表。

## 沿用課程樣式

只可唯讀參考 [demo.html](../../../starter/src/finops_agent/demo.html) 的主題 script 與 CSS tokens：
使用完整 Clawpilot `--cp-*` 變數、light/dark CSS，以及 `scoutTheme`／`prefers-color-scheme` 偵測；主題 script 放在其他 JS 前。
所有元件色彩使用 `var(--cp-*)`，不要複製該檔案的 admin、API、輪詢或登入程式。

字體使用 `"Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif`；
等寬字使用 `Consolas, "Courier New", Courier, monospace`。間距採 4px 倍數，一般元件圓角 `0.625rem`，卡片 `16px` 並保留輕量陰影。

## 交付與修正

先簡述讀取欄位、檢核方式及畫面安排，再提出單一 HTML 的變更。
請使用者檢視後自行開啟、選取 JSON，確認總數、單位、切換／排序及錯誤提示。
不要把未實際開啟的頁面說成已完成瀏覽器驗證。

若要求修正，先指出證據欄位與差異，再只修改使用者指定的 HTML；不修改 evidence 來讓數字看起來一致。
