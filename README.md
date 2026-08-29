# 股票工具（Financial Terminal）

以 Python 與 pywebview 製作的台股桌面工具，提供自選股、行情輪播、個股資訊、ETF 成分股分析、基本面篩選與績效回測。

## 主要功能

- 搜尋台股與 ETF：可依代號或中文名稱搜尋，並直接加入自選股。
- 自選股管理：從市場卡片或個股詳細頁加入／移除，資料會儲存至 SQLite。
- 即時報價與市場輪播：使用 Yahoo Finance 取得報價。
- 個股詳細資訊：開收盤、歷史價格、走勢圖與除息紀錄。
- FinMind 優先來源：設定 Token 後，台股詳細資訊優先使用 FinMind；無 Token、資料不足、連線失敗、Token 無效或額度不足時，自動回退 Yahoo Finance。
- ETF 成分股重疊分析。
- 自選股基本面快篩。
- 歷史回測與績效比較。
- 系統匣常駐：關閉視窗後會隱藏，可從系統匣顯示或結束。

## 桌面版架構

程式使用 pywebview 直接在內嵌視窗中執行 HTML 介面，JavaScript 透過 `window.pywebview.api` 呼叫 Python。

因此桌面版：

- 不啟動 Uvicorn／FastAPI HTTP 伺服器。
- 不監聽 `localhost`、`127.0.0.1` 或任何 TCP port。
- 無法由外部或本機瀏覽器透過網址直接開啟。

`api_*.py` 中既有的資料處理函式會由 `desktop_bridge.py` 重用；FastAPI 路由保留作為程式碼相容層，但桌面版不會啟動它們。

## FinMind 使用方式

1. 在 FinMind 官網取得 API Token。
2. 啟動程式，按右上角「系統設定」。
3. 貼上 Token 並儲存。
4. 開啟台股個股詳細資訊，標題會顯示實際資料來源：`FinMind` 或 `Yahoo Finance`。

為避免超過 FinMind 每小時 API 用量：

- 同一檔股票的日價格資料會快取 5 分鐘。
- 同一檔股票的除權息資料會快取 24 小時。
- FinMind 請求失敗時，5 分鐘內會直接改用 Yahoo Finance，避免重複發送失敗請求。

快取只存在程式記憶體，關閉程式後會清除。SQLite 資料庫 `market_room.db` 則保存自選股與設定值。

## 開發環境

需求：Python 3.12（建議）與 Windows。

```powershell
py -3.12 -m venv env
.\env\Scripts\Activate.ps1
pip install -r requirements.txt
```

以開發模式啟動桌面版：

```powershell
python run.py
```

## 打包 Windows 執行檔

```powershell
python -m PyInstaller willyStocks.spec --noconfirm
```

完成後執行：

```powershell
.\dist\willyStocks.exe
```

每次修改 Python 或 HTML 後都必須重新打包，`dist\willyStocks.exe` 才會包含最新變更。

## GitHub Releases 更新

`update.py` 可從 GitHub Releases 檢查與下載新版。使用前請先在 `update.py` 修改：

```python
GITHUB_REPOSITORY = "你的 GitHub 帳號/Repository 名稱"
```

每次建立正式版 Release 時：

1. 使用數字版本 Tag，例如 `v0.2.0`。
2. 上傳檔名固定為 `willyStocks.exe` 的執行檔資產。
3. 將專案根目錄的 `version.json` 版本同步改為該版本，再重新打包。
4. 使用者必須先關閉股票工具，再執行：

```powershell
python update.py
```

可用 `python update.py --check` 只檢查是否有新版。若想讓使用者不需安裝 Python，可額外打包更新器：

```powershell
python -m PyInstaller update.py --onefile --noconsole --name update
```

將 `update.exe`、`willyStocks.exe` 與 `version.json` 放在同一資料夾即可使用。也可在 Release 額外上傳 `willyStocks.exe.sha256`，更新器便會自動驗證下載檔案。

主程式啟動後也會在背景檢查一次最新正式 Release。只有偵測到新版且同資料夾存在 `update.exe` 時，才會顯示更新確認視窗；使用者確認後才會下載與替換檔案。

更新器會顯示「等待主程式關閉」、「正在下載新版」與「正在安裝新版」的進度視窗。若 EXE 仍被 Windows 暫時鎖定，會持續等待並重試 30 秒；成功或失敗時會顯示結果，成功後按確認會自動啟動新版程式。

## 專案結構

```text
desktop_app.py      pywebview 桌面程式進入點
desktop_bridge.py   前端 JavaScript 與 Python 的內部橋接
dashboard.html      使用者介面
api_*.py            各項資料查詢、分析與設定邏輯
db.py               SQLite 初始化與連線
market_room.db      自選股與設定資料庫
willyStocks.spec    PyInstaller 打包設定
```
