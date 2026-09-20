# 學員手冊：打造 Copilot FinOps Agent

這次一起做三件事：**找出用量成長的原因 → 申請並核准額度 → 換成 Foundry 模型**。
先完成每段的主要成果，再決定要不要加做選配項目。

| 階段 | 你會做出什麼 |
| --- | --- |
| Lab 1 | 一頁有證據的決策摘要；也可以加做網頁 dashboard |
| Lab 2 | 使用者提出申請，管理者核准，畫面顯示新額度 |
| Lab 3（選配） | 同一個 Agent 改用 Foundry Model，或觀摩講師示範 |

我們使用 **2026/9/1–9/22 的模擬資料**，不是你的真實帳單。AI credits 也不是原始 tokens。
報表工具在本機執行；Copilot／Foundry 的模型仍是線上服務，可能產生使用費用。

## 先把環境開起來

用 VS Code 開啟 **repo 根目錄**，也就是看得到 `starter/`、`solution/` 的資料夾。
先確認 Python 是 **3.13**，再選一組命令操作。不是 3.13 或遇到錯誤時，先看 [環境準備](environment-prep.md)。

第一次使用要建立 `.venv`；這個資料夾不會隨 GitHub repo 提供。
已完成課前安裝的人，只需啟用既有環境、設定變數，不必重新安裝。

PowerShell：

```powershell
python --version
python -m venv .\starter\.venv
& .\starter\.venv\Scripts\Activate.ps1
python -m pip install -r .\starter\requirements.txt
$env:PYTHONPATH = (Resolve-Path .\starter\src).ProviderPath
$env:FINOPS_BACKEND = "mock"
$env:FINOPS_ALLOW_REAL_WRITES = "false"
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
export FINOPS_ALLOW_REAL_WRITES=false
python -m finops_agent --data-dir data cost
```

看到 **34,906.67 AI credits／USD 329.12**，就表示範例資料讀進來了。
先保留這個終端；另外開終端時，記得重新啟用環境並設定 `PYTHONPATH`。

## Lab 1：讓 Copilot 幫忙查原因

這次不用貼一大段操作規則：repo 已附上調查與 dashboard 兩個 **skills**，幫 Copilot 記住做事方式。
它們放在 `.github/skills/`，跟 repo 一起提供，不用另外下載或安裝。

### 1. 給它一個任務

在 **GitHub Copilot Chat** 選 **Agent** 模式，輸入：

```text
/finops-investigation 本月 AI credits 成長異常。請找出主要原因，預估月底用量，提出兩個改善方案
```

Copilot 會先看趨勢，再依需要查使用者、模型、團隊與執行紀錄。先不要把講師答案或整包資料附給它。
展開工具呼叫，看看它是否真的查過資料；看到要安裝、改原始碼或連外的操作，先停下來。

找不到 skill 時，先確認開的是 repo 根目錄，再輸入 `/skills` 查看。
也可以把 [調查 SKILL.md](../.github/skills/finops-investigation/SKILL.md) 附到 Chat，說「請照這份 skill 調查」。
其他問題見 [疑難排解](troubleshooting.md)。

### 2. 先猜，再看證據

第一輪結果出來時，先和同組同學猜：**用最多的團隊，就是最浪費的嗎？**
接著回覆 Copilot：「繼續查工作量與成功成果，再判斷原因。」

重點不是背欄位，而是分清楚：工作真的變多了，還是同一件事被做了好幾次？
如果 Copilot 太早下結論，追問：「哪一項證據支持這個判斷？」

### 3. 選兩個方案，交代理由

請 Copilot 比較三個方向：**修正重複觸發、簡單任務換模型、短期增加預算**。
各組選兩個，說明可能的好處、風險，以及誰要確認。增加預算是支持工作，不是省錢。

把成長原因、月底估算、兩個選擇和沒選另一個的理由整理成一頁。
檢視內容後，請 Copilot 存到 `workshop-output/finops-review.md`；已有同名檔案就換新名字。

**Checkpoint 1：** 你能拿出證據，說明原因、成功成果、月底估算與兩個方案，不只是列一張用量排行榜。

### 選做：把結果做成網頁 dashboard

這是加做項目，跳過也能進 Lab 2。**先完成調查與選案**，再於終端匯出證據：

```powershell
python -m finops_agent --data-dir data brief --include-investigation --output .\workshop-output\lab1-evidence.json
```

bash 將輸出路徑改為 `workshop-output/lab1-evidence.json`。檔案已存在就換新名字，不覆蓋原檔。
回到 Agent Chat，附上這份 JSON，輸入：

```text
/finops-dashboard 用 workshop-output/lab1-evidence.json 製作本機 dashboard
```

如果用了新檔名，記得一起改上面的路徑。[Dashboard skill](../.github/skills/finops-dashboard/SKILL.md) 會要求單一 HTML，不用安裝套件或開 server。
先檢視變更，再自己開啟 `workshop-output/finops-dashboard.html`，用頁面的選檔鈕載入 JSON。

看看總數、趨勢、成功成果與方案是否對得回證據。數字有問題，就在同一段 Chat 說：「請照 skill 核對資料，只修正這個 HTML。」
不要把認證、真實資料或管理者功能放進網頁。選做卡住時，先保留作品、接著做 Lab 2。

## Lab 2：讓 Agent 替你申請額度

現在扮演 **carol**。她還有遷移工作要完成，希望提高限額；另一位同學或講師扮演管理者。
這是本機 mock 演練，不會調整真實 GitHub 預算。

### 1. 接上 SDK

先完成 [Lab 2 模型認證](environment-prep.md#lab-2-模型認證)，並在已啟用的環境下載 runtime：

```powershell
python -m copilot download-runtime
```

只需編輯 `starter/src/finops_agent/demo_connection.py`，把內容接成下面這樣：

```python
from .budget_demo import USER_INSTRUCTIONS, BudgetDemo
from .harness import CopilotFinOpsHarness


def build_demo_harness(service: BudgetDemo) -> CopilotFinOpsHarness:
    return CopilotFinOpsHarness(
        service.toolbox,
        custom_tools=service.user_tools(),
        instructions=USER_INSTRUCTIONS,
    )
```

執行 `python -m pytest starter/checks/test_lab2.py -q` 確認接線。
這裡的模型只拿到個人工具，不能查其他團隊，也不能自己核准。

### 2. 開兩個分頁

保留 `FINOPS_BACKEND=mock`、`FINOPS_ALLOW_REAL_WRITES=false`，啟動：

```powershell
python -m finops_agent demo
```

把終端提供的 **User** 和 **Admin** 連結各開一個分頁。
Admin 連結交給管理者保管，不要分享或截圖；持有它就能操作這次 mock 核准。
若 port 被占用，改用 `python -m finops_agent demo --port 8099`。

### 3. 提問、申請，再由人核准

在 User 頁面先問：「我目前花費多少？有什麼節省建議？」
接著說：

> 請把每月限額提高到 USD 220，因為月底前還有 60 個遷移批次要完成，請管理者核准。

看到 **pending（待核准）** 時，額度應該還沒改。
換管理者檢查申請人、金額與理由，再按 **核准並套用 mock 額度**；也約定月底檢視，不假設系統會自動調回額度。

回 User 頁面看 **approved（已核准）**，再問一次：「現在還有多少額度？」

| 階段 | 限額 | 已用 | 剩餘 |
| --- | --- | --- | --- |
| 開始／待核准 | 150 | 102.67 | 47.33 |
| 管理者核准後 | 220 | 102.67 | 117.33 |

**Checkpoint 2：** 跑完「提問 → 申請 → 人核准 → 新額度」。已用金額不變，模型不能代替人核准。

如果模型連不上，可用頁面上「直接提交 mock 申請（不經模型）」繼續練習，但這不代表模型呼叫成功。
重開 demo 會恢復初始資料，舊連結也會失效。

## Lab 3：換成 Foundry Model（選配）

主辦方已準備好模型與權限就跟著做，否則觀摩講師。
**這段只換模型，不加入 Toolbox 或其他服務，也不用先部署到雲端。**

### 1. 停止 demo，改模型設定

先按 `Ctrl+C`。下面的 endpoint 和 deployment name 請填主辦方提供的值。
`foundry-identity` 使用已授權的開發者身分；若主辦方提供 API key，改照 [模型設定](environment-prep.md#lab-3-foundry-model-課前準備) 使用 `AZURE_OPENAI_API_KEY`，不要貼進 Chat。

PowerShell：

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

### 2. 重跑同一個問題

開啟**新的** User／Admin 連結，再查花費、申請 220、由管理者核准。
重啟會重設 mock 資料；換模型不會改變工具權限或核准規則。

要看到 SDK 聊天真正回覆，才算模型接通；只有數字卡片或備援表單正常還不夠。
如果連不上就看講師示範，或停止程序、改回 `FINOPS_MODEL_PROVIDER=copilot`，使用原本可用的 token 再啟動。

**Checkpoint 3：** 說得出「換了模型，但資料、工具與人工核准流程沒有變」。
Foundry 推論費用由 Azure 另計，mock GitHub budget 不會限制它。

想繼續部署，而且主辦方已備妥 hosting 環境時，再看 [選配 Hosted 部署](hosted-deployment.md)。
請分開記錄「模型接通」「Hosted 部署完成」或「觀摩」，不要混為一談。

## 卡住時

Lab 1 先請 TA 一起看下一步要查什麼；skill 找不到或工具失敗，見 [疑難排解](troubleshooting.md)。
Lab 2 接線卡住，可以從 repo 根目錄還原參考答案：

```powershell
python .\scripts\checkpoint.py --lab 2
python -m pytest .\starter\checks -q
```

bash 用 `python scripts/checkpoint.py --lab 2`。
工具會先備份編輯，不覆蓋 `.env` 或 `workshop-output/` 裡的摘要、JSON 和 dashboard。

## 離開前

停止本機 demo／host、退出 chat，清掉 shell 認證並撤銷課程專用 token。
不要提交 `.env`、真實資料、session history 或 audit logs。

```powershell
Remove-Item Env:COPILOT_GITHUB_TOKEN,Env:AZURE_OPENAI_API_KEY -ErrorAction SilentlyContinue
```

bash 用 `unset COPILOT_GITHUB_TOKEN AZURE_OPENAI_API_KEY`。
Azure 資源由主辦方統一清理，不要自行對共用資源執行 `azd down`。
