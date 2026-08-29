import numpy as np
import pandas as pd
from fastapi import APIRouter
import yfinance as yf

router = APIRouter()


@router.get("/api/backtest-with-indicators")
def get_backtest_with_indicators(symbols: str, period: str = "1y"):
    try:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return {"error": "請提供有效的股票代號"}

        clean_symbols = [
            s + ".TW"
            if not s.endswith((".TW", ".TWO")) and not s.startswith("^")
            else s
            for s in symbol_list
        ]

        price_data = {}
        for sym, clean_sym in zip(symbol_list, clean_symbols):
            ticker = yf.Ticker(clean_sym)
            df = ticker.history(period=period)
            if not df.empty:
                price_data[sym] = df["Close"]

        if not price_data:
            return {"error": "找不到任何有效的歷史資料"}

        combined_df = pd.DataFrame(price_data).dropna()
        if combined_df.empty:
            return {"error": "選取的股票在該區間內沒有交集對齊的交易日"}

        labels = [d.strftime("%Y-%m-%d") for d in combined_df.index]
        datasets = []
        colors = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]

        metrics_summary = {}

        for i, sym in enumerate(symbol_list):
            if sym not in combined_df.columns:
                continue

            series = combined_df[sym]
            initial_price = series.iloc[0]
            
            # 1. 累積報酬率百分比
            returns = ((series / initial_price) - 1) * 100

            # 2. 計算 20 日移動平均線（MA20）
            ma20 = series.rolling(window=20).mean()
            ma20_returns = ((ma20 / initial_price) - 1) * 100

            # 3. 計算最大回撤 (Max Drawdown, MDD)
            rolling_max = series.cummax()
            drawdown = (series - rolling_max) / rolling_max
            max_drawdown = drawdown.min() * 100

            base_color = colors[i % len(colors)]

            # 將 pandas Series 中的 NaN 替換為 Python 的 None (對應 JSON 的 null)
            clean_returns = [None if pd.isna(x) else round(float(x), 2) for x in returns]
            clean_ma20 = [None if pd.isna(x) else round(float(x), 2) for x in ma20_returns]

            # 主報酬率線
            datasets.append({
                "label": f"{sym} 實際報酬率",
                "data": clean_returns,
                "borderColor": base_color,
                "backgroundColor": base_color,
                "borderWidth": 2,
                "fill": False,
                "tension": 0.1,
            })

            # MA20 趨勢輔助線
            datasets.append({
                "label": f"{sym} MA20 趨勢",
                "data": clean_ma20,
                "borderColor": base_color,
                "borderDash": [4, 4],
                "borderWidth": 1.5,
                "fill": False,
                "tension": 0.2,
            })

            metrics_summary[sym] = {
                "total_return": round(float(returns.iloc[-1]), 2),
                "max_drawdown": round(float(max_drawdown), 2)
            }

        return {
            "labels": labels, 
            "datasets": datasets,
            "metrics": metrics_summary
        }
    except Exception as e:
        return {"error": str(e)}


# 相容舊路由名稱
get_backtest_data = get_backtest_with_indicators