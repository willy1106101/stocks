import yfinance as yf
import pandas as pd
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/backtest")
def get_backtest_data(symbols: str, period: str = "1y"):
    try:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return {"error": "請提供有效的股票代號"}

        # 整理代號格式
        clean_symbols = [
            s + ".TW" if not s.endswith((".TW", ".TWO")) and not s.startswith("^") else s 
            for s in symbol_list
        ]
        
        price_data = {}
        for sym, clean_sym in zip(symbol_list, clean_symbols):
            ticker = yf.Ticker(clean_sym)
            df = ticker.history(period=period)
            if not df.empty:
                price_data[sym] = df['Close']

        if not price_data:
            return {"error": "找不到任何有效的歷史資料"}

        # 組合所有代號的收盤價，並用 dropna() 確保時間軸與交易日完全對齊
        combined_df = pd.DataFrame(price_data).dropna()
        if combined_df.empty:
            return {"error": "選取的股票在該區間內沒有交集對齊的交易日"}

        # 取得統一的日期標籤
        labels = [d.strftime('%Y-%m-%d') for d in combined_df.index]
        datasets = []
        colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

        for i, sym in enumerate(symbol_list):
            if sym not in combined_df.columns:
                continue
            
            series = combined_df[sym]
            initial_price = series.iloc[0]
            returns = ((series / initial_price) - 1) * 100

            datasets.append({
                "label": sym,
                "data": returns.round(2).tolist(),
                "borderColor": colors[i % len(colors)],
                "backgroundColor": colors[i % len(colors)],
                "borderWidth": 2,
                "fill": False,
                "tension": 0.1
            })

        return {"labels": labels, "datasets": datasets}
    except Exception as e:
        return {"error": str(e)}