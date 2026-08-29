from fastapi import APIRouter
import twstock
import yfinance as yf

router = APIRouter()

@router.get("/api/quotes")
def get_batch_quotes(symbols: str = ""):
    if not symbols:
        return []
        
    results = []
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    
    for sym in sym_list:
        try:
            if sym in twstock.codes:
                info = twstock.codes[sym]
                suffix = ".TW" if info.market == "上市" else ".TWO"
                
                ticker = yf.Ticker(f"{sym}{suffix}")
                price = ticker.fast_info.last_price
                prev_close = ticker.fast_info.previous_close
                
                if price is not None and prev_close is not None:
                    change = price - prev_close
                    percent = (change / prev_close * 100) if prev_close else 0
                    results.append({
                        "symbol": sym,
                        "name": info.name,
                        "price": round(float(price), 2),
                        "change": round(float(change), 2),
                        "percent": round(float(percent), 2)
                    })
            else:
                ticker = yf.Ticker(sym)
                price = ticker.fast_info.last_price
                prev_close = ticker.fast_info.previous_close
                
                if price is not None and prev_close is not None:
                    change = price - prev_close
                    percent = (change / prev_close * 100) if prev_close else 0
                    results.append({
                        "symbol": sym, 
                        "name": sym,
                        "price": round(float(price), 2),
                        "change": round(float(change), 2),
                        "percent": round(float(percent), 2)
                    })
        except Exception:
            continue
            
    return results