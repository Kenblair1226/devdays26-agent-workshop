# 學員手冊：打造 Copilot FinOps Agent

這次我們一起做 **3 個 Labs**：先用 GitHub Copilot Chat 看懂費用資料，再接上 Copilot SDK，試試「使用者申請額度、管理者核准」，最後把同一個 harness 的模型換成 Foundry Model；完成模型切換且環境就緒後，再選配把 Agent 部署到 Foundry。

**Lab 1 用現成工具找證據、提出決策；Lab 2 接上 SDK，讓查詢與申請流程串起來**。想把調查結果做得更好讀，也可以在 Lab 1 選做網頁 dashboard。需要參考時，可以看 `solution/` 裡的完整版本。

## 今天要解決什麼問題？

想像你是虛構組織 `octo-demo` 的平台工程師，主管突然問：

> 「這個月哪個部門用了最多 AI credits？主要花在哪些模型？有沒有節省的空間？」

我們會讓 Agent 幫忙查資料、找出值得注意的地方，再提出建議。遇到 seat 或 budget 的調整，則由人來決定要不要核准。

先提醒一下：**程式在本機跑，不代表模型也離線運作。** Lab 1 的報表工具不需認證，但 Copilot Chat 需要在 VS Code 登入有權限的 GitHub 帳號；Lab 2 的 SDK 聊天另需 Copilot token 或主辦方提供的 BYOK。前兩個 Lab 都不用先準備 Foundry hosting 資源。

每一段先完成核心成果，再依學員進度與環境狀態決定是否進入選配內容。

| 階段 | 做完會看到什麼 |
| --- | --- |
| 情境、架構與安全界線 | 分辨 model runtime、tools、hosting |
| 啟動課前環境 | 本機 `cost` 成功 |
| Lab 1：用 Copilot 做 FinOps 調查 | 一頁有數據依據的決策摘要 |
| Lab 2：使用者／管理者 demo | 查費用、節省建議、提高限額、核准後更新 |
| Lab 3：Foundry Model 與選配部署 | 換模型重跑同一個情境，再自行部署或觀摩 demo |
| 講師延伸示範與討論 | 資料、權限、觀測的限制 |
| 成果核對、清理 | 關閉程序、移除認證 |

## 先把環境開起來

先在 **repo 根目錄，也就是看得到 `starter/` 和 `solution/` 的地方**，開啟終端。剛 clone 下來沒有 `starter/.venv/` 是正常的：這是每台電腦自己建立的 Python 虛擬環境，不能直接從 GitHub 下載別人的來用，也不會提交到 Git。

第一次使用，照下面順序做：**確認 Python 3.13 → 建立 `.venv` → 啟用 → 安裝依賴 → 跑範例**。如果課前已經建立環境並安裝好依賴，之後開新終端只需啟用環境、設定變數，再執行範例，不必重建。

PowerShell 和 bash 選一組就好。練習時都用 `starter/`，不要在同一個 Python 程序裡混用兩個版本；Python 還沒安裝或遇到認證問題時，請看 [環境準備](environment-prep.md)。

PowerShell 7：

```powershell
python --version
python -m venv .\starter\.venv
& .\starter\.venv\Scripts\Activate.ps1
python -m pip install -r .\starter\requirements.txt
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
python -m finops_agent --data-dir .\data cost
```

bash：

```bash
python3.13 --version
python3.13 -m venv starter/.venv
source starter/.venv/bin/activate
python -m pip install -r starter/requirements.txt
export PYTHONPATH="$PWD/starter/src"
export FINOPS_BACKEND=mock
python -m finops_agent --data-dir data cost
```

版本應顯示 **3.13.x**；如果不是，先停下來選對 Python 再建立環境。如果 bash 裡的 `python` 已經是 3.13，也可以用 `python -m venv starter/.venv`。建立失敗時不要接著跑 `source`，先找 TA 檢查錯誤。

進入 Lab 2 前，建議在啟用的環境中先跑一次 `python -m copilot download-runtime`，把 SDK runtime 下載好。Lab 1 的報表工具不需要這個下載；詳情在 [環境準備](environment-prep.md)。

看到 `net_quantity=4760`、`net_amount=44.88`、`currency=USD`，就表示資料讀進來了。

我們用的是 **`2026-09-22T23:59:59Z`** 的範例快照，所以這裡的 `month_to_date` 固定指 **2026-09-01～2026-09-22（含首尾，共 22 天）**，不是你上課當天。這些都是**合成教學數字**：即使你在 9/22 之前打開，也會看到預先模擬的後續日期；那不是未來的真實觀測，也不是預測或正式 GitHub 帳單。AI credits 更不是原始 token 數。

## Lab 1：用 GitHub Copilot 做 FinOps 調查

先從主管的問題出發，拿工具產生的證據，請 Copilot 幫忙回答三件事：**錢花在哪裡、預算合不合理、接下來該做什麼**。全程使用 mock 資料，不需要真實 organization 的權限。

### 1. 先準備要交給 Copilot 的資料

確認 `FINOPS_BACKEND=mock`，用現成工具產生分析用的 JSON，再檢查工具與資料是否正常：

```powershell
python -m finops_agent brief --output .\workshop-output\lab1-evidence.json
python -m pytest .\starter\checks\test_lab1.py -q
```

bash：

```bash
python -m finops_agent brief --output workshop-output/lab1-evidence.json
python -m pytest starter/checks/test_lab1.py -q
```

這個工具檢查在課程提供的 starter 應該通過。它只能告訴你工具和資料沒問題，Copilot 等一下的回答還是要自己核對。

如果檔案已經存在，換個名字，例如 `python -m finops_agent brief --output workshop-output/lab1-evidence-v2.json`，再跑一次；工具不會覆蓋舊檔。新版分析包的 `schema_version=2`，包含 `daily_usage`。若手上的舊輸出缺少它，請重新產生，接下來的附件與選檔也要改用**新檔名**。`brief` 只是把 mock 資料整理起來，不會呼叫模型、建立變更計畫或修改 seats。

打開 JSON，可以先認識這幾個 section，不用逐行讀完：

| Section | 可以拿來看什麼 |
| --- | --- |
| `cost_summary`、`department_ranking` | 總用量、部門排行、Unallocated |
| `daily_usage` | 9/1～9/22 每日樣本、各日 net credits／USD，以及 coverage 與缺漏限制 |
| `model_breakdown`、`user_breakdown`、`leading_department_models` | 找出用量集中在哪些人／模型，深入第一名部門 |
| `seat_inventory`、`optimization_hypotheses` | 閒置疑點、未知 activity、改善假設 |
| `budget_review` | 各 budget 自己的 consumed、remaining、scope 與 hard stop |
| `run_rate_scenario` | 給定 USD 80 情境的月末外推；不是實際預算餘額 |

這次把原本的合成月累計重新分配成有高低變化的每日樣本，保留 **4,760 net AI credits / USD 44.88**，不是往真實帳單追加觀測。Billing 宣告的訓練視窗是 **2026-08-26～2026-09-22**，類型為 `sparse_training_samples`；8 月只提供 8/31 的樣本，未提供的日期不是已知的零。9 月雖然每天都有樣本，也不能據此宣稱拿到了真實組織的完整帳務。詳細口徑見 [資料說明](../data/README.md)。

### 2. 請 Copilot 找出成本熱點

在 VS Code 開啟 **GitHub Copilot Chat**，選 **Ask** 模式，再把 `workshop-output/lab1-evidence.json` 加進附件或 context。

只附這份合成資料就夠了，**不要附 `.env`、公司報表或 admin token，也不用整個 repo 都丟進去**。這時 Copilot 是在讀你給它的報表，還沒有接到我們的 SDK harness。

先貼上這段試試：

> 你是 FinOps 分析師，只依據附件，不修改程式、不呼叫外部 API、不執行管理動作。
> 先告訴我這份資料涵蓋哪段時間、as_of 是什麼、金額和用量各用什麼單位，以及資料有哪些限制。
> 這個月哪個部門用了最多 net AI credits？它占全部 credits 和 net amount 各幾 %？
> 再幫我看這個部門主要用了哪些模型。也比較一下 Platform Engineering 和 Security：credits 排名跟金額排名一樣嗎？
> 每個結論都附上對應的 JSON section、欄位和計算式。記得保留 Unallocated，也別直接把高用量當成浪費。

看完回答，別急著全盤接受。跑 `python -m finops_agent departments` 或 `python -m finops_agent breakdown --dimension model`，對照一下數字。如果某句話看不出依據，就追問：「哪個欄位支持這個結論？」

### 3. 預算合理嗎？哪些 seats 真的該回收？

留在**同一段 Chat**，接著問：

> 再幫我檢查預算和 seats：
> 1. 用 budget_review 裡每筆 consumed_amount 算出使用率和 remaining，比較 organization budget 和 carol 的 user budget。這些限制分別會影響誰？
> 2. 為什麼不能把 run_rate_scenario 當成 organization budget 的真實餘額，或拿來斷言哪天一定超支？
> 3. 有哪些人的 seat activity 太久沒更新，或根本不知道？請對照 user_breakdown 和使用紀錄，特別看 ivan 和 judy。
> 請分成「已確認的事實／矛盾或不足的證據／還要問什麼／建議下一步」。先不要給我一份直接回收 seats 的名單。

這裡有個容易踩到的坑：activity 很舊，不代表這期完全沒用；`null` 也不等於「從未使用」。同樣地，找不到成本中心歸屬時，應該先補資料，不能隨便塞到某個部門，或乾脆不算那筆用量。

### 4. 比較兩個節省方案

接著做個 what-if，看看不同做法可能帶來什麼影響：

> 幫我比較兩個方案，並把假設寫清楚：
> A. 假設 AI Lab 透過縮小 context 和模型 routing 實驗，讓「相同資料期間」的 net amount 降低 10%，差額會是多少？
> B. 假設主管另外確認，下個月可以回收 1 個 seat，以教學假設月費 USD 19 來算，下個月的 license fee 可以少多少？
> 請分別列出時間範圍、計算式、品質或可用性風險，以及需要誰核准。不要把不同期間的金額直接加成總節省，也不要把 credits 換算成 tokens。
> 如果要談 ROI，還缺哪些導入成本和效益資料？code acceptance rate 不能直接當作投資報酬率。

記得，這只是**「如果這樣做，可能會怎樣」的估算**，不是已經省下來的錢。便宜模型能不能完成任務、品質有沒有下降、credit pool 會不會受影響，都要一起考慮。

### 5. 整理成一頁，準備拿給主管看

最後請 Copilot 幫你整理：

> 幫我把剛才的分析整理成一頁繁體中文 FinOps 決策摘要，包含：
> - 3 個發現：附資料來源 section、數字、期間和限制。
> - 2 個優先行動：說明依據、預期影響、風險、誰負責、誰核准，以及下次怎麼看成效。事實和假設請分開寫。
> - 1 個「現在先不做」的動作，並說明原因。
> - 一筆待核准的調整建議，例如 carol 的 user budget，寫出目前值 → 建議值、理由和 hard-stop 設定。只提議，不要真的執行。

自己讀一遍、修正不合理的地方，再存成 `workshop-output/finops-review.md`。這份就是你這一段的成果；目錄已被 Git 忽略，不會自動進入版本控制。

**Checkpoint 1：做到這裡就算完成。** 你能說明「錢花在哪裡、接下來想做什麼、哪些事還不能決定」，並拿出一次跨表比對、兩個有來源的行動，以及一個先不做的理由。答案不用和別人一模一樣，重點是你能講清楚依據；測試通過不能取代這份摘要。

### 選做（optional）：請 Copilot 幫你把用量做成網頁 dashboard

想讓主管更容易看懂趨勢嗎？可以把**同一份 mock evidence** 做成一頁本機 dashboard。這是 Lab 1 的延伸，不是第四個 Lab、新服務或繳交要求；**Checkpoint 1 仍然是一頁決策摘要**，跳過這段也能直接進 Lab 2。

剛才用 **Ask** 模式分析附件，現在改用 VS Code 的 **GitHub Copilot Chat → Agent** 模式，讓 Copilot 提議建立檔案。沿用 VS Code 既有的 Copilot 登入即可；**不要把 API key、token、`.env` 或真實組織資料放進 prompt 或瀏覽器**。產生後的網頁本身不需要模型認證。

#### 先限定它能讀什麼、改哪裡

1. 附上剛產生、含 `daily_usage` 的 `workshop-output/lab1-evidence.json`。若你用了 `lab1-evidence-v2.json`，把下面 prompt 的資料檔名一起換掉。
2. 只允許建立 `workshop-output/finops-dashboard.html`。若已有作品，先選新名字，例如 `finops-dashboard-v2.html`，並更新 prompt；不要覆蓋舊成果。
3. 可讓 Copilot **唯讀**參考 `starter/src/finops_agent/demo.html` 的樣式；不是拿它當資料來源，也不是複製管理者功能。
4. 檢視 Copilot 提議的 edits 與工具操作，再接受變更。若提議改 repo source、`.env`、安裝套件或開 server，先拒絕，請它回到單一 HTML 的範圍。先看過檔案，再由你手動開啟；不要自動執行或上傳生成結果。

把這段貼給 Copilot：

```text
請幫我把 Lab 1 的合成用量資料做成一頁繁體中文 FinOps dashboard。

範圍：
- 唯一資料來源是附件 workshop-output/lab1-evidence.json；請先讀懂實際 JSON 欄位，不猜 schema，不把下列驗收數字硬編成畫面資料。
- 唯一可建立／編輯的檔案是 workshop-output/finops-dashboard.html；已存在就先停止，讓我指定新檔名。不要改 repo source、.env、資料集或其他檔案。
- starter/src/finops_agent/demo.html 只可唯讀參考樣式：重用完整 Clawpilot --cp-* 變數、light/dark CSS 和 scoutTheme／prefers-color-scheme 的主題偵測機制，主題 script 放在其他 JS 前。所有元件色彩只用 var(--cp-*)；字體用 "Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif，等寬字用 Consolas, "Courier New", Courier, monospace。採 4px 間距、一般元件 0.625rem 圓角、卡片 16px 與輕量陰影。不要複製它的 admin、API、輪詢或登入行為。
- 交付單一自含 HTML/CSS/JavaScript；用 vanilla SVG/CSS 畫圖。不要 npm、框架安裝、CDN、外部字型、網路呼叫、fetch、SDK、API、backend、server、登入或任何 persistence（含 localStorage、cookie）。不要 seat／budget 變更按鈕或 approval tools。不要執行命令、自動開啟或上傳結果。

資料載入與錯誤：
- 頁面初始顯示空白狀態說明和有 label 的 JSON 選檔 input，先不要顯示數字或假圖。用瀏覽器 File API 讀取使用者選的檔案，再 JSON.parse；讓 file:// 直接開啟也能用，不靠 fetch 或 server。
- 驗證 schema_version=2、必備 section／欄位／型別、有限數值、日期範圍與 as_of 一致性；daily_usage.items 日期須唯一且排序。資料缺漏、格式錯誤、舊版缺 daily_usage 或加總不一致時，清掉舊圖與數字，顯示可讀的錯誤和重新產生 evidence 的建議，不能補成零。
- daily_usage.items 的 net_quantity 與 net_amount 必須分別加總核對 cost_summary；金額以 cents 檢核，避免浮點誤差。核對 items 與 missing_dates 是否符合 period，不自己補觀測。
- 所有來自 JSON 的文字（含名稱、source、limitations、錯誤內容）都以 textContent 呈現，不使用 innerHTML 或當成程式執行。選檔、切換與排序支援鍵盤、可見焦點；錯誤用 role=alert。每張圖都附可閱讀的資料表和清楚的單位。

畫面：
1. 醒目標示「Synthetic data／合成教學資料」、snapshot、固定 MTD 起訖、currency=USD、unit=AI credits、source、coverage、limitations。日期可能是預先模擬的未來日期，不是預測、即時使用量、真實帳單或原始 tokens。
2. cost_summary 提供 net AI credits 與 net USD 兩張 KPI；金額與 credits 永遠分開，不相加、不互換。
3. 每日趨勢只讀 daily_usage.items，依 date 畫 net_amount 或 net_quantity，提供單位切換與同資料表。只畫提供的樣本；missing_dates 應標成未知並斷線，不補零或插值。顯示 daily_samples 與 sparse_training_samples 的限制。
4. 部門排行讀 department_ranking.ranking，模型排行讀 model_breakdown.items；保留 Unallocated 與所有資料列，可依提供的 net credits／金額欄位排序。不要從日彙總臆造「依部門／模型篩選每日趨勢」；排序或單位切換不能改全體 KPI、期間或加總。
5. 獨立 budget 表讀 budget_review.budgets，每筆沿用自己的 scope、限額、已用、剩餘與 hard-stop 欄位（欄名以附件為準，例如 consumed_amount）；不可用 billing 金額覆蓋 budget snapshot。獨立 seat 表讀 seat_inventory.seats，保留它自己的 activity 資訊，null 顯示未知，不能自動判成可回收。
6. run_rate_scenario 另放情境區，按原始欄位呈現假設與限制，與 billing、budget、seat 表分開。外推不是已出帳金額、實際 budget 餘額或保證超支日。

先說明你會讀哪些欄位、如何核對加總，再提出這一個 HTML 檔案的變更，讓我檢視。
```

#### 自己開啟、選檔，再對答案

接受前，先看 diff：是否只有指定的 HTML？有沒有外連、讀取認證或帶入管理者功能？確認後，從檔案總管雙擊 `workshop-output/finops-dashboard.html`，或把這個檔案拖進瀏覽器。**不需要 `npm install`、啟動 server 或調整 CORS**。

應先看到選檔說明。用頁面的選檔鈕載入**新版** evidence JSON，而不是期待網頁自己找相對路徑。檔案只留在此頁記憶體；重新整理後再選一次即可。

| 要核對什麼 | 這份 mock evidence 的答案 |
| --- | --- |
| Snapshot／MTD | `2026-09-22T23:59:59Z`；2026-09-01～2026-09-22 |
| 全體 KPI／每日樣本加總 | 4,760 net AI credits／USD 44.88 |
| AI Lab／Unallocated | 2,400 credits／USD 26；90 credits／USD 0.54 |
| 每日趨勢 | 22 個 9 月日期，最後是 9/22；`missing_dates=[]`，每天有樣本不代表真實帳務完整 |
| Organization budget（獨立快照） | 限額 80、已用 45.20、剩餘 34.80；不是 billing 的 44.88 |
| carol budget（尚未進 Lab 2 核准） | 限額 20、已用 14、剩餘 6 |
| Run-rate 情境（不是實際預算） | 44.88 ÷ 22 × 30 = USD 61.20；`projected_over_budget=false`，情境目前餘額 35.12 不是 org 的 34.80 |

切換 credits／USD、切換排行排序後，再核對一次全體總數。也檢查空白狀態與錯誤處理：若選到損壞 JSON 或缺 `daily_usage` 的舊 evidence，應顯示錯誤，而不是一張全零或沿用舊數字的圖。舊版請用新檔名重新產生，並在 Chat 與網頁都換成新檔。

有差異時，可以接著貼這段；仍只允許改剛才指定的 HTML：

```text
請用我附的新版 mock evidence 檢查剛才的 dashboard，只修正指定 HTML，先列出差異的 JSON 欄位與原因，不修改或捏造資料，也不自動執行或上傳。
這份資料應加總為 4760 credits／44.88 USD，AI Lab 2400／26，Unallocated 90／0.54；daily_usage 應有 22 個 9 月日期並在 2026-09-22 結束。
確認 organization budget 仍是 consumed 45.20／remaining 34.80，carol 是 consumed 14／limit 20／remaining 6，沒有被 billing 或 forecast 覆蓋。
確認排序／單位切換不改總數，也沒有臆造部門或模型的每日篩選。
修正損壞 JSON、缺 daily_usage、缺欄位與不一致加總的錯誤提示；缺日期標未知並斷線，不補零。舊 evidence 必須提示用新檔名重新產生。
```

圖畫得漂亮只是第一步，**數字能對回證據、限制說得清楚**，才是這個選做練習的重點。如果 Agent 模式不可用，或頁面還需要調整，保留決策摘要、先進 Lab 2 就好。

**接著進 Lab 2。** 剛才是你手動準備資料、附檔、追問。下一段把模型和工具接起來，讓 Agent 自己查資料，再試一次「提出申請 → 管理者核准」。

## Lab 2：接上 SDK，體驗申請與管理者核准

這次換你扮演 **carol**：你想知道自己花了多少、有沒有節省空間，也想為下週專案提高額度。請另一位同學或講師當管理者，兩個人用同一台電腦的不同分頁操作。

這是本機 mock 角色演示，**不是正式的 SSO 登入或 RBAC 權限系統**，資料也不會寫到真實 GitHub。

### 1. 補幾行，把 SDK 接上來

工具、提示詞、畫面和核准邏輯都準備好了。打開 `starter/src/finops_agent/demo_connection.py`，找到 `build_demo_harness()`，把 TODO 換成：

```python
return CopilotFinOpsHarness(
    service.toolbox,
    custom_tools=service.user_tools(),
    instructions=USER_INSTRUCTIONS,
)
```

再補上 `from .budget_demo import USER_INSTRUCTIONS`，其他 imports 已經有了。跑 `python -m pytest starter/checks/test_lab2.py -q` 看看是否接對。**不用自己填多份 schema，也不用複製 UUID 或在聊天裡貼 approval token。**

這幾行做的事，就是把工具和提示詞交給 harness，讓它串起模型與工具。使用者能用的工具只有 `get_my_costs`、`get_my_savings`、`request_budget_increase`；帳號由伺服器決定，不會因為你在 prompt 說「我是 admin」就改變。模型也拿不到核准工具。

### 2. 開兩個分頁，一個當使用者、一個當管理者

先照 [Lab 2 認證](environment-prep.md#lab-2-模型認證) 設好模型憑證。保留剛才的 `PYTHONPATH` 和 `FINOPS_BACKEND=mock`，然後跑：

```powershell
python -m finops_agent demo
```

bash 也是同一個命令。終端會出現兩個 `http://127.0.0.1:8098/` 連結，分別帶有這次啟動專用的角色存取碼。把 **User** 和 **Admin** 開在兩個分頁，並排看最清楚。

User 由使用者操作，Admin 由管理者保管。**不要把 admin link 交給使用者或截圖分享**；持有它就能操作這次 demo 的管理者功能。重啟後，舊連結就不能用了。如果 port 被占用，改跑 `python -m finops_agent demo --port 8099`。

先看一下 User 頁面：carol 本期應該用了 **1,400 net AI credits / USD 14**，限額 **USD 20**、已用 **14**、剩餘 **6**。這裡只看 carol，不是 Lab 1 的全組織金額 44.88；用量仍是範例快照，不是即時帳務。

### 3. 先問「我花了多少？」再問「怎麼省？」

在 User 頁面按快捷問題，或自己輸入：

> 我目前花費多少？額度還剩多少？

> 有什麼節省 AI credits 的建議？請附資料依據，不要直接降低我的額度。

留意畫面上顯示了哪些工具名稱，再看看回答有沒有引用資料。SDK 會依問題選工具，但只能查目前使用者的範圍。節省建議可以是縮小 context、讓不同模型處理不同難度的任務，並比較品質；不能直接說「你已經省了多少 tokens」。

### 4. 申請加額，再換管理者核准

接著在 User 頁面說：

> 請把我的每月限額提高到 USD 30，理由是下週有 migration 專案。

模型會呼叫 `request_budget_increase`，畫面出現 **pending（待核准）**。先停一下，看看數字：**限額應該還是 20，剩餘還是 6**。「申請送出」和「已經核准」是兩回事。

現在換管理者操作另一個分頁。確認申請人是 carol、金額是 **20 → 30**，再看一下理由和提交時間。都沒問題後，點 **核准並套用 mock 額度**。這一步必須由人確認，模型不能自己核准。

回到 User 頁面，等它自動更新成 **approved（已核准）**。這時限額應該是 **30**、已用 **14** 不變、剩餘 **16**。再問一次：「我的申請核准了嗎？現在可用額度是多少？」看看 Agent 是否真的重新查了資料，而不是重複剛才的答案。

### 5. 確認整個流程真的跑完了

| 階段 | 限額 | 已用 | 剩餘 | 狀態 |
| --- | --- | --- | --- | --- |
| 開始 | 20 | 14 | 6 | 尚未申請 |
| 使用者申請 | 20 | 14 | 6 | pending |
| 管理者核准 | 30 | 14 | 16 | approved |

**Checkpoint 2：** 對照上表，確認你跑完了「提問 → 建議 → 申請 → 人核准 → 新限額」。管理者頁面的 audit 也應留下核准和執行紀錄。記住這幾條界線：使用者不能存取管理者 API、模型沒有 approve tool，同一筆申請重複核准也不能重複變更。

頁面每三秒更新一次，只是在讀 mock 狀態，不會一直呼叫模型或消耗 model tokens。

如果模型連不上，先別卡在這裡。可以改用畫面上的 **直接提交 mock 申請（不經模型）** 表單，繼續體驗待核准、核准和餘額更新。只是要說清楚：這是備援操作，不代表 SDK 聊天已經成功。重啟 demo 會清除申請並恢復範例額度；這組 UI 和核准 API 只在 localhost 使用，不會跟著 Lab 3 部署。

想多玩一點，可以課後再看 `chat` 的 `/plans`、`/approve` 和 seat 管理；今天不用把這些全部做完。

## Lab 3：換成 Foundry Model，再選配部署（可改 Demo）

這段只加 **Foundry Model**，先不加入 Toolbox 或其他服務。重點是看見：**模型可以換，SDK harness、工具和人工核准流程不必重寫。** Lab 1/2 照原本的 Copilot 路線完成即可，不會因為你沒有 Azure 權限就卡住。

完成 Lab 2 的核心流程後，先聽講師說明。主辦方已準備好模型和權限就自己操作；如果沒有，直接觀摩講師 demo。這裡的「換模型」只需要模型可用，**不需要先把 Agent 部署到雲端**，也不用現場建立 Azure 資源。

### 1. 換模型，重跑熟悉的使用者／管理者情境

先在 Lab 2 的終端按 `Ctrl+C` 停止 demo。**重啟會重設 mock 申請、回到限額 20／已用 14／剩餘 6，兩個角色連結也會更新**；這是重啟造成的，不是換模型會修改帳務。

下面把主辦方課前提供的 **endpoint** 和 **model deployment name** 填進 `AZURE_OPENAI_ENDPOINT`、`MODEL_NAME`。`foundry-identity` 在本機使用你已登入、已授權的開發者身分，`AZURE_OPENAI_API_KEY` 可以留空；部署後才使用 Managed Identity。若主辦方採 API key，改照 [Foundry Model 認證方式](environment-prep.md#lab-3-foundry-model-課前準備) 的三個 `.env` 變數設定即可。

PowerShell（仍在 repo 根目錄、使用同一個 venv 與 `PYTHONPATH`）：

```powershell
$env:FINOPS_BACKEND = "mock"
$env:FINOPS_ALLOW_REAL_WRITES = "false"
$env:FINOPS_MODEL_PROVIDER = "foundry-identity"
$env:AZURE_OPENAI_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:MODEL_NAME = "<model-deployment-name>"
python -m finops_agent demo
```

bash：

```bash
export FINOPS_BACKEND=mock
export FINOPS_ALLOW_REAL_WRITES=false
export FINOPS_MODEL_PROVIDER=foundry-identity
export AZURE_OPENAI_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export MODEL_NAME="<model-deployment-name>"
python -m finops_agent demo
```

把 `<...>` 換成課前分配給你的值，不要填 GitHub 模型名稱或 Hosted Agent endpoint。`AZURE_OPENAI_ENDPOINT` 也可填主辦方提供的 Azure OpenAI 資源根網址；`/openai/v1` 由程式補上，不會重複加。開啟終端顯示的**新 User／Admin 連結**，再試同一組問題：

1. User 問：「我目前花費多少？額度還剩多少？」
2. User 問：「有什麼節省 AI credits 的建議？」
3. User 說：「請提高到 USD 30，理由是下週有 migration 專案。」
4. 確認仍是 **pending、限額 20**，再由 Admin 核准，看到 **限額 30、已用 14、剩餘 16**。

回答的措辭可以不同，但 evidence、工具權限與核准規則不能變。模型不能自己 approve，也不能把 carol 變成管理者。看見卡片還不夠：它們本來就能從 mock 資料讀出來，要有**經 SDK 聊天得到的回覆**，才算完成模型切換；不要把備援表單當成模型呼叫成功。

記得分清楚兩筆帳：畫面上的 GitHub Copilot credits／budget 是**被分析的合成資料**；Agent 呼叫 Foundry Model 產生的 inference 費用由 Azure 計費。把 carol 的 budget 提到 30，不會調整 Azure quota 或限制 Azure 費用，也不能據此宣稱換模型比較省。

如果 Foundry 模型或權限不通，不要反覆重試。看講師預備的 demo，或停止程序後改回 `FINOPS_MODEL_PROVIDER=copilot`，確認 `COPILOT_MODEL` 和 `COPILOT_GITHUB_TOKEN` 是原本可用的值，再重新啟動。回到 Copilot 是備案，不算 Foundry Model 已連上。

### 2. 選配：把 Agent 部署到 Foundry

只有主辦方已完成 hosting 環境準備才繼續；否則看講師既有 endpoint 即可。如果部署受阻，就改看講師 demo，不必全班停下來等，也不犧牲成果核對。

打開 `starter/azure.yaml`，找到這幾行：

```yaml
host: azure.ai.agent
codeConfiguration:
  runtime: python_3_13
  entryPoint: main.py
```

這表示我們直接交出 Python 程式，由 Foundry 負責執行，不用自己準備 Dockerfile。`main.py` 裡的 `InvocationAgentServerHost` 收到 `{"input":"..."}` 後，會呼叫同一個 SDK harness。模型設定使用 `FINOPS_MODEL_PROVIDER=foundry-identity`，透過 Managed Identity 存取已部署的模型。

有一點和 Lab 2 不同：這個 Hosted 範例的**每次請求都使用獨立的 mock 狀態**，不會共用聊天紀錄或核准結果。Lab 2 的管理者頁面不會一起上雲，也不要把它當成正式的核准服務。真實寫入仍只限講師的受控流程。

#### 部署後，問它同一個問題

先停止剛才的本機 demo，再確認主辦方已把你的**個人環境**綁定到 `starter/.azure/`，前兩個 checkpoints 也都完成了。這裡直接用附好的 `starter/request.example.json`，省去手動處理 JSON 引號和編碼的麻煩。

PowerShell：

```powershell
Push-Location .\starter
$previousUserAgent = $env:AZURE_DEV_USER_AGENT
try {
    $env:AZURE_DEV_USER_AGENT = "microsoft_foundry_skill"
    azd deploy finops-agent --no-prompt
    if ($LASTEXITCODE -ne 0) { throw "Deploy failed; use instructor demo." }
    azd ai agent invoke --protocol invocations -f .\request.example.json
    if ($LASTEXITCODE -ne 0) { throw "Invoke failed; use instructor demo." }
    azd ai agent monitor
}
finally {
    $env:AZURE_DEV_USER_AGENT = $previousUserAgent
    Pop-Location
}
```

bash（整段執行完會回到原目錄）：

```bash
(
  cd starter &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy finops-agent --no-prompt &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent invoke --protocol invocations -f request.example.json &&
  AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent monitor
)
```

收到回應後，找找 `reply`、`invocation_id`、`tool_calls` 和 `backend=mock`。把答案和 Lab 1 的數字對照一下，再用 monitor 看同一次請求呼叫了哪些工具。

Monitor 預設只取近期 console logs，想持續看才加 `--follow`。這次不另外建立 tracing 服務，也別把 console logs 當成完整的模型 token trace。

### 3. 換了什麼？哪些事情沒有變？

**Checkpoint 3：** 能說出「換的是 model provider，SDK、mock 資料與人工核准流程不變」，就是這段的核心成果。也請分清楚 **本機 harness 呼叫 Foundry Model** 與 **Hosted Agent 部署完成**，兩件事要分開記錄。

你可以自行完成，或跟著講師看相同流程。如果只完成模型切換，就記錄模型呼叫成功、hosting 未執行；如果沒有雲端資源，就記為觀摩，不要把本機結果說成「已部署 Foundry」。

## 跟不上時，先用參考答案接著做

如果 Lab 2 卡住了，回到 repo 根目錄跑下面的命令。工具會先把你的編輯備份到 `.workshop-backups/`，再還原那個 Lab 的檔案：

```powershell
python .\scripts\checkpoint.py --lab 2
python -m pytest .\starter\checks -q
```

bash 用 `python scripts/checkpoint.py --lab 2`。它不會刪掉工作目錄，也不會覆蓋 `.env` 或 `workshop-output/` 裡的 evidence、`finops-review.md` 與選做的 `finops-dashboard.html`。

如果 Lab 1 卡在分析，先整理出一個有依據的行動和一個「暫時不做」的決定，和 TA 核對後再接著做。選做 dashboard 卡住也可以先保留檔案；這些是分析成果，不是 source checkpoint 的還原目標。

## 離開前，記得收尾

記得退出 chat、停止本機 demo／host，並清掉 shell 裡的認證。`.env`、真實資料、runtime history 和 audit log 都不要提交到 Git。

Azure 資源會由主辦方統一關閉，**不要自行對共用 resource group 執行 `azd down`**。

```powershell
Remove-Item Env:COPILOT_GITHUB_TOKEN,Env:AZURE_OPENAI_API_KEY -ErrorAction SilentlyContinue
```

bash 用 `unset COPILOT_GITHUB_TOKEN AZURE_OPENAI_API_KEY`。如果用了課程專用的短期 token，課後也到 GitHub 把它撤銷。
