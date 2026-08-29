import yfinance as yf
from fastapi import APIRouter
import twstock

router = APIRouter()

@router.get("/api/fundamentals")
def get_fundamentals(symbols: str):
    try:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
        results = []
        
        for sym in symbol_list:
            clean_sym = sym + ".TW" if not sym.endswith((".TW", ".TWO")) and not sym.startswith("^") else sym
            ticker = yf.Ticker(clean_sym)
            info = ticker.info
            
            # 從 twstock 取得中文名稱，若找不到則使用 yfinance 的名稱或代號
            stock_name = sym
            if sym in twstock.codes:
                stock_name = twstock.codes[sym].name
            else:
                stock_name = info.get("shortName", sym)
            
            pe = info.get("trailingPE")
            pb = info.get("priceToBook")
            div_yield = info.get("dividendYield")
            m_cap = info.get("marketCap")
            rev_growth = info.get("revenueGrowth")
            
            # 修正殖利率顯示邏輯（防範 yfinance 數值格式不一致的問題）
            if div_yield:
                if div_yield > 1:
                    # 若大於 1，代表它本身已是百分比格式或需安全縮放
                    val = div_yield if div_yield <= 15 else div_yield / 100
                    if val > 15:
                        val = val / 100
                else:
                    # 若小數點格式，則乘以 100 轉為百分比
                    val = div_yield * 100
                formatted_yield = f"{round(val, 2)}%"
            else:
                formatted_yield = "N/A"
            
            results.append({
                "symbol": sym,
                "name": stock_name,
                "peRatio": round(pe, 2) if pe else "N/A",
                "pbRatio": round(pb, 2) if pb else "N/A",
                "dividendYield": formatted_yield,
                "marketCap": f"{round(m_cap / 1e8, 1)} 億" if m_cap else "N/A",
                "revenueGrowth": f"{round(rev_growth * 100, 2)}%" if rev_growth else "N/A"
            })
            
        return results
    except Exception as e:
        return {"error": str(e)}