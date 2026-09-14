# 學員手冊：打造 Copilot FinOps Agent

接下來的 **90 分鐘，我們一起做 3 個 Labs**：先用 GitHub Copilot Chat 看懂費用資料，再接上 Copilot SDK，試試「使用者申請額度、管理者核准」，最後把同一個 harness 的模型換成 Foundry Model；環境和時間允許時，再把 Agent 部署到 Foundry。

不用擔心要從零開始寫程式：**Lab 1 的工具都準備好了；Lab 2 只補幾行 SDK 接線**。需要參考時，可以看 `solution/` 裡的完整版本。

## 今天要解決什麼問題？

想像你是虛構組織 `octo-demo` 的平台工程師，主管突然問：

> 「這個月哪個部門用了最多 AI credits？主要花在哪些模型？有沒有節省的空間？」

我們會讓 Agent 幫忙查資料、找出值得注意的地方，再提出建議。遇到 seat 或 budget 的調整，則由人來決定要不要核准。

先提醒一下：**程式在本機跑，不代表模型也離線運作。** Lab 1 的報表工具不需認證，但 Copilot Chat 需要在 VS Code 登入有權限的 GitHub 帳號；Lab 2 的 SDK 聊天另需 Copilot token 或主辦方提供的 BYOK。前兩個 Lab 都不用先準備 Foundry hosting 資源。

| 時間 | 要做什麼 | 做完會看到什麼 |
| --- | --- | --- |
| 0–8 分 | 情境、架構與安全界線 | 分辨 model runtime、tools、hosting |
| 8–15 分 | 啟動課前環境 | 本機 `cost` 成功 |
| 15–37 分 | Lab 1：用 Copilot 做 FinOps 調查 | 一頁有數據依據的決策摘要 |
| 37–63 分 | Lab 2：使用者／管理者 demo | 查費用、節省建議、提高限額、核准後更新 |
| 63–78 分 | Lab 3：Foundry Model 與選配部署 | 換模型重跑同一個情境，再自行部署或觀摩 demo |
| 78–86 分 | 講師延伸示範與討論 | 資料、權限、觀測的限制 |
| 86–90 分 | 成果核對、清理 | 關閉程序、移除認證 |

## 先把環境開起來

如果還沒做過，先照 [環境準備](environment-prep.md) 完成安裝。接著在 **repo 根目錄，也就是看得到 `starter/` 和 `solution/` 的地方**，開啟終端。

下面分成 PowerShell 和 bash，選你正在使用的那一組就好。練習時都用 `starter/`，不要在同一個 Python 程序裡混用兩個版本。

PowerShell 7：

```powershell
& .\starter\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
python -m finops_agent --data-dir .\data cost
```

bash：

```bash
source starter/.venv/bin/activate
export PYTHONPATH="$PWD/starter/src"
export FINOPS_BACKEND=mock
python -m finops_agent --data-dir data cost
```

看到 `net_quantity=4760`、`net_amount=44.88`、`currency=USD`，就表示資料讀進來了。

我們用的是 **2026-09-03 UTC** 的範例快照，所以這裡的 `month_to_date` 指 9 月 1–3 日，不是你上課當天。這些都是**合成教學數字**，別把它當成正式 GitHub 價格、帳單或原始 token 數。

## Lab 1：用 GitHub Copilot 做 FinOps 調查（22 分鐘，免寫程式）

這一段先不寫程式。我們直接拿準備好的工具和資料，請 Copilot 幫忙回答三件事：**錢花在哪裡、預算合不合理、接下來該做什麼**。全程使用 mock 資料，不需要真實 organization 的權限。

### 1. 先準備要交給 Copilot 的資料（3 分鐘）

工具已經寫好了，不用改 `analytics.py`。確認 `FINOPS_BACKEND=mock`，跑下面兩個命令，產生分析用的 JSON 並檢查工具是否正常：

```powershell
python -m finops_agent brief --output .\workshop-output\lab1-evidence.json
python -m pytest .\starter\checks\test_lab1.py -q
```

bash：

```bash
python -m finops_agent brief --output workshop-output/lab1-evidence.json
python -m pytest starter/checks/test_lab1.py -q
```

這個 checkpoint **不需要改程式就應該通過**。它只能告訴你工具和資料沒問題，Copilot 等一下的回答還是要自己核對。

如果檔案已經存在，換個名字，例如 `lab1-evidence-v2.json`，再跑一次；工具不會覆蓋舊檔。`brief` 只是把 mock 資料整理起來，不會呼叫模型、建立變更計畫或修改 seats。

打開 JSON，可以先認識這幾個 section，不用逐行讀完：

| Section | 可以拿來看什麼 |
| --- | --- |
| `cost_summary`、`department_ranking` | 總用量、部門排行、Unallocated |
| `model_breakdown`、`user_breakdown`、`leading_department_models` | 找出用量集中在哪些人／模型，深入第一名部門 |
| `seat_inventory`、`optimization_hypotheses` | 閒置疑點、未知 activity、改善假設 |
| `budget_review` | 各 budget 自己的 consumed、remaining、scope 與 hard stop |
| `run_rate_scenario` | 給定 USD 80 情境的月末外推；不是實際預算餘額 |

### 2. 請 Copilot 找出成本熱點（5 分鐘）

在 VS Code 開啟 **GitHub Copilot Chat**，選 **Ask** 模式，再把 `workshop-output/lab1-evidence.json` 加進附件或 context。

只附這份合成資料就夠了，**不要附 `.env`、公司報表或 admin token，也不用整個 repo 都丟進去**。這時 Copilot 是在讀你給它的報表，還沒有接到我們的 SDK harness。

先貼上這段試試：

> 你是 FinOps 分析師，只依據附件，不修改程式、不呼叫外部 API、不執行管理動作。
> 先告訴我這份資料涵蓋哪段時間、as_of 是什麼、金額和用量各用什麼單位，以及資料有哪些限制。
> 這個月哪個部門用了最多 net AI credits？它占全部 credits 和 net amount 各幾 %？
> 再幫我看這個部門主要用了哪些模型。也比較一下 Platform Engineering 和 Security：credits 排名跟金額排名一樣嗎？
> 每個結論都附上對應的 JSON section、欄位和計算式。記得保留 Unallocated，也別直接把高用量當成浪費。

看完回答，別急著全盤接受。跑 `python -m finops_agent departments` 或 `python -m finops_agent breakdown --dimension model`，對照一下數字。如果某句話看不出依據，就追問：「哪個欄位支持這個結論？」

### 3. 預算合理嗎？哪些 seats 真的該回收？（6 分鐘）

留在**同一段 Chat**，接著問：

> 再幫我檢查預算和 seats：
> 1. 用 budget_review 裡每筆 consumed_amount 算出使用率和 remaining，比較 organization budget 和 carol 的 user budget。這些限制分別會影響誰？
> 2. 為什麼不能把 run_rate_scenario 當成 organization budget 的真實餘額，或拿來斷言哪天一定超支？
> 3. 有哪些人的 seat activity 太久沒更新，或根本不知道？請對照 user_breakdown 和使用紀錄，特別看 ivan 和 judy。
> 請分成「已確認的事實／矛盾或不足的證據／還要問什麼／建議下一步」。先不要給我一份直接回收 seats 的名單。

這裡有個容易踩到的坑：activity 很舊，不代表這期完全沒用；`null` 也不等於「從未使用」。同樣地，找不到成本中心歸屬時，應該先補資料，不能隨便塞到某個部門，或乾脆不算那筆用量。

### 4. 比較兩個節省方案（4 分鐘）

接著做個 what-if，看看不同做法可能帶來什麼影響：

> 幫我比較兩個方案，並把假設寫清楚：
> A. 假設 AI Lab 透過縮小 context 和模型 routing 實驗，讓「相同資料期間」的 net amount 降低 10%，差額會是多少？
> B. 假設主管另外確認，下個月可以回收 1 個 seat，以教學假設月費 USD 19 來算，下個月的 license fee 可以少多少？
> 請分別列出時間範圍、計算式、品質或可用性風險，以及需要誰核准。不要把不同期間的金額直接加成總節省，也不要把 credits 換算成 tokens。
> 如果要談 ROI，還缺哪些導入成本和效益資料？code acceptance rate 不能直接當作投資報酬率。

記得，這只是**「如果這樣做，可能會怎樣」的估算**，不是已經省下來的錢。便宜模型能不能完成任務、品質有沒有下降、credit pool 會不會受影響，都要一起考慮。

### 5. 整理成一頁，準備拿給主管看（4 分鐘）

最後請 Copilot 幫你整理：

> 幫我把剛才的分析整理成一頁繁體中文 FinOps 決策摘要，包含：
> - 3 個發現：附資料來源 section、數字、期間和限制。
> - 2 個優先行動：說明依據、預期影響、風險、誰負責、誰核准，以及下次怎麼看成效。事實和假設請分開寫。
> - 1 個「現在先不做」的動作，並說明原因。
> - 一筆待核准的調整建議，例如 carol 的 user budget，寫出目前值 → 建議值、理由和 hard-stop 設定。只提議，不要真的執行。

自己讀一遍、修正不合理的地方，再存成 `workshop-output/finops-review.md`。這份就是你這一段的成果；目錄已被 Git 忽略，不會自動進入版本控制。

**Checkpoint 1：做到這裡就算完成。** 你能說明「錢花在哪裡、接下來想做什麼、哪些事還不能決定」，並拿出一次跨表比對、兩個有來源的行動，以及一個先不做的理由。答案不用和別人一模一樣，重點是你能講清楚依據；測試通過不能取代這份摘要。

**接著進 Lab 2。** 剛才是你手動準備資料、附檔、追問。下一段把模型和工具接起來，讓 Agent 自己查資料，再試一次「提出申請 → 管理者核准」。

## Lab 2：接上 SDK，體驗申請與管理者核准（26 分鐘）

這次換你扮演 **carol**：你想知道自己花了多少、有沒有節省空間，也想為下週專案提高額度。請另一位同學或講師當管理者，兩個人用同一台電腦的不同分頁操作。

這是本機 mock 角色演示，**不是正式的 SSO 登入或 RBAC 權限系統**，資料也不會寫到真實 GitHub。

### 1. 補幾行，把 SDK 接上來（6 分鐘）

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

### 2. 開兩個分頁，一個當使用者、一個當管理者（4 分鐘）

先照 [Lab 2 認證](environment-prep.md#lab-2-模型認證) 設好模型憑證。保留剛才的 `PYTHONPATH` 和 `FINOPS_BACKEND=mock`，然後跑：

```powershell
python -m finops_agent demo
```

bash 也是同一個命令。終端會出現兩個 `http://127.0.0.1:8098/` 連結，分別帶有這次啟動專用的角色存取碼。把 **User** 和 **Admin** 開在兩個分頁，並排看最清楚。

User 由使用者操作，Admin 由管理者保管。**不要把 admin link 交給使用者或截圖分享**；持有它就能操作這次 demo 的管理者功能。重啟後，舊連結就不能用了。如果 port 被占用，改跑 `python -m finops_agent demo --port 8099`。

先看一下 User 頁面：carol 本期應該用了 **1,400 net AI credits / USD 14**，限額 **USD 20**、已用 **14**、剩餘 **6**。這裡只看 carol，不是 Lab 1 的全組織金額 44.88；用量仍是範例快照，不是即時帳務。

### 3. 先問「我花了多少？」再問「怎麼省？」（5 分鐘）

在 User 頁面按快捷問題，或自己輸入：

> 我目前花費多少？額度還剩多少？

> 有什麼節省 AI credits 的建議？請附資料依據，不要直接降低我的額度。

留意畫面上顯示了哪些工具名稱，再看看回答有沒有引用資料。SDK 會依問題選工具，但只能查目前使用者的範圍。節省建議可以是縮小 context、讓不同模型處理不同難度的任務，並比較品質；不能直接說「你已經省了多少 tokens」。

### 4. 申請加額，再換管理者核准（8 分鐘）

接著在 User 頁面說：

> 請把我的每月限額提高到 USD 30，理由是下週有 migration 專案。

模型會呼叫 `request_budget_increase`，畫面出現 **pending（待核准）**。先停一下，看看數字：**限額應該還是 20，剩餘還是 6**。「申請送出」和「已經核准」是兩回事。

現在換管理者操作另一個分頁。確認申請人是 carol、金額是 **20 → 30**，再看一下理由和提交時間。都沒問題後，點 **核准並套用 mock 額度**。這一步必須由人確認，模型不能自己核准。

回到 User 頁面，等它自動更新成 **approved（已核准）**。這時限額應該是 **30**、已用 **14** 不變、剩餘 **16**。再問一次：「我的申請核准了嗎？現在可用額度是多少？」看看 Agent 是否真的重新查了資料，而不是重複剛才的答案。

### 5. 確認整個流程真的跑完了（3 分鐘）

| 階段 | 限額 | 已用 | 剩餘 | 狀態 |
| --- | --- | --- | --- | --- |
| 開始 | 20 | 14 | 6 | 尚未申請 |
| 使用者申請 | 20 | 14 | 6 | pending |
| 管理者核准 | 30 | 14 | 16 | approved |

**Checkpoint 2：** 對照上表，確認你跑完了「提問 → 建議 → 申請 → 人核准 → 新限額」。管理者頁面的 audit 也應留下核准和執行紀錄。記住這幾條界線：使用者不能存取管理者 API、模型沒有 approve tool，同一筆申請重複核准也不能重複變更。

頁面每三秒更新一次，只是在讀 mock 狀態，不會一直呼叫模型或消耗 model tokens。

如果模型連不上，先別卡在這裡。可以改用畫面上的 **直接提交 mock 申請（不經模型）** 表單，繼續體驗待核准、核准和餘額更新。只是要說清楚：這是備援操作，不代表 SDK 聊天已經成功。重啟 demo 會清除申請並恢復範例額度；這組 UI 和核准 API 只在 localhost 使用，不會跟著 Lab 3 部署。

想多玩一點，可以課後再看 `chat` 的 `/plans`、`/approve` 和 seat 管理；今天不用把這些全部做完。

## Lab 3：換成 Foundry Model，再選配部署（15 分鐘，可改 Demo）

這段只加 **Foundry Model**，先不加入 Toolbox 或其他服務。重點是看見：**模型可以換，SDK harness、工具和人工核准流程不必重寫。** Lab 1/2 照原本的 Copilot 路線完成即可，不會因為你沒有 Azure 權限就卡住。

到了第 63 分鐘，先聽講師說明。主辦方已準備好模型和權限就自己操作；如果沒有，直接觀摩講師 demo。這裡的「換模型」只需要模型可用，**不需要先把 Agent 部署到雲端**，也不用現場建立 Azure 資源。

### 1. 換模型，重跑熟悉的使用者／管理者情境（5 分鐘）

先在 Lab 2 的終端按 `Ctrl+C` 停止 demo。**重啟會重設 mock 申請、回到限額 20／已用 14／剩餘 6，兩個角色連結也會更新**；這是重啟造成的，不是換模型會修改帳務。

下面用主辦方課前提供的 **Foundry project endpoint** 和 **model deployment name**。`foundry-identity` 在本機使用你已登入、已授權的開發者身分；部署後才使用 Managed Identity。若主辦方採 API key，改照 [Foundry Model 認證方式](environment-prep.md#lab-3-foundry-model-課前準備) 設定即可。

PowerShell（仍在 repo 根目錄、使用同一個 venv 與 `PYTHONPATH`）：

```powershell
$env:FINOPS_BACKEND = "mock"
$env:FINOPS_ALLOW_REAL_WRITES = "false"
$env:FINOPS_MODEL_PROVIDER = "foundry-identity"
$env:FOUNDRY_PROJECT_ENDPOINT = "https://<account>.services.ai.azure.com/api/projects/<project>"
$env:AZURE_AI_MODEL_DEPLOYMENT_NAME = "<model-deployment-name>"
python -m finops_agent demo
```

bash：

```bash
export FINOPS_BACKEND=mock
export FINOPS_ALLOW_REAL_WRITES=false
export FINOPS_MODEL_PROVIDER=foundry-identity
export FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="<model-deployment-name>"
python -m finops_agent demo
```

把 `<...>` 換成課前分配給你的值，不要填 GitHub 模型名稱或 Hosted Agent endpoint。開啟終端顯示的**新 User／Admin 連結**，再試同一組問題：

1. User 問：「我目前花費多少？額度還剩多少？」
2. User 問：「有什麼節省 AI credits 的建議？」
3. User 說：「請提高到 USD 30，理由是下週有 migration 專案。」
4. 確認仍是 **pending、限額 20**，再由 Admin 核准，看到 **限額 30、已用 14、剩餘 16**。

回答的措辭可以不同，但 evidence、工具權限與核准規則不能變。模型不能自己 approve，也不能把 carol 變成管理者。看見卡片還不夠：它們本來就能從 mock 資料讀出來，要有**經 SDK 聊天得到的回覆**，才算完成模型切換；不要把備援表單當成模型呼叫成功。

記得分清楚兩筆帳：畫面上的 GitHub Copilot credits／budget 是**被分析的合成資料**；Agent 呼叫 Foundry Model 產生的 inference 費用由 Azure 計費。把 carol 的 budget 提到 30，不會調整 Azure quota 或限制 Azure 費用，也不能據此宣稱換模型比較省。

如果 Foundry 模型或權限不通，不要反覆重試。看講師預備的 demo，或停止程序後改回 `FINOPS_MODEL_PROVIDER=copilot`，確認 `COPILOT_MODEL` 和 `COPILOT_GITHUB_TOKEN` 是原本可用的值，再重新啟動。回到 Copilot 是備案，不算 Foundry Model 已連上。

### 2. 選配：把 Agent 部署到 Foundry（7 分鐘）

只有主辦方已完成 hosting 環境準備才繼續；否則看講師既有 endpoint 即可。部署等候超過 5 分鐘也切換 demo，不犧牲最後的成果核對。

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

### 3. 換了什麼？哪些事情沒有變？（3 分鐘）

能說出「換的是 model provider，SDK、mock 資料與人工核准流程不變」，就是這段的核心成果。也請分清楚 **本機 harness 呼叫 Foundry Model** 與 **Hosted Agent 部署完成**，兩件事要分開記錄。

你可以自行完成，或跟著講師看相同流程。如果只完成模型切換，就記錄模型呼叫成功、hosting 未執行；如果沒有雲端資源，就記為觀摩，不要把本機結果說成「已部署 Foundry」。

## 跟不上時，先用參考答案接著做

如果 Lab 2 卡住了，回到 repo 根目錄跑下面的命令。工具會先把你的編輯備份到 `.workshop-backups/`，再還原那個 Lab 的檔案：

```powershell
python .\scripts\checkpoint.py --lab 2
python -m pytest .\starter\checks -q
```

bash 用 `python scripts/checkpoint.py --lab 2`。它不會刪掉工作目錄，也不會覆蓋 `.env` 或 `workshop-output/finops-review.md`。

Lab 1 沒有 code TODO，不需要還原。時間不夠時，先整理出一個有依據的行動和一個「暫時不做」的決定，再跟上下一段就好。

## 離開前，花一分鐘收尾

記得退出 chat、停止本機 demo／host，並清掉 shell 裡的認證。`.env`、真實資料、runtime history 和 audit log 都不要提交到 Git。

Azure 資源會由主辦方統一關閉，**不要自行對共用 resource group 執行 `azd down`**。

```powershell
Remove-Item Env:COPILOT_GITHUB_TOKEN,Env:FOUNDRY_API_KEY -ErrorAction SilentlyContinue
```

bash 用 `unset COPILOT_GITHUB_TOKEN FOUNDRY_API_KEY`。如果用了課程專用的短期 token，課後也到 GitHub 把它撤銷。
