import math
from datetime import date, timedelta
from threading import Lock
from time import monotonic
from fastapi import APIRouter
import requests
import twstock
import yfinance as yf
import traceback
from db import get_db_connection

router = APIRouter()
FINMIND_DATA_URL = "https://api.finmindtrade.com/api/v4/data"
FINMIND_CACHE_TTL = {
    "TaiwanStockPrice": 5 * 60,
    "TaiwanStockDividendResult": 24 * 60 * 60,
}
FINMIND_FAILURE_TTL = 5 * 60
_finmind_cache = {}
_finmind_failures = {}
_finmind_cache_lock = Lock()

def safe_float(val, default=0.0):
    try:
        if val is None:
            return default
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, 2)
    except (ValueError, TypeError):
        return default

def get_finmind_token() -> str:
    """Read the optional FinMind token saved through the settings screen."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", ("finmind_token",)
        ).fetchone()
        return row["value"].strip() if row and row["value"] else ""
    finally:
        conn.close()


def fetch_finmind_dataset(token: str, dataset: str, symbol: str, start_date: str):
    """Return a FinMind dataset, or ``None`` when it cannot be used.

    A failure is intentionally silent here: the caller falls back to the
    original Yahoo Finance implementation so an invalid token never breaks the
    desktop application.
    """
    cache_key = (token, dataset, symbol)
    now = monotonic()
    with _finmind_cache_lock:
        cached = _finmind_cache.get(cache_key)
        if cached and now - cached[0] < FINMIND_CACHE_TTL[dataset]:
            return cached[1]

        # Prevent a bad token, temporary outage, or quota response from being
        # retried on every 15-second carousel refresh.
        failed_at = _finmind_failures.get(cache_key)
        if failed_at and now - failed_at < FINMIND_FAILURE_TTL:
            return None

    try:
        response = requests.get(
            FINMIND_DATA_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "dataset": dataset,
                "data_id": symbol,
                "start_date": start_date,
                "end_date": date.today().isoformat(),
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in (200, "200"):
            raise ValueError("FinMind returned an unsuccessful status")
        records = payload.get("data")
        if not isinstance(records, list):
            raise ValueError("FinMind returned an invalid data payload")
        with _finmind_cache_lock:
            _finmind_cache[cache_key] = (monotonic(), records)
            _finmind_failures.pop(cache_key, None)
        return records
    except (requests.RequestException, ValueError, TypeError):
        with _finmind_cache_lock:
            _finmind_failures[cache_key] = monotonic()
        return None


def get_finmind_stock_detail(symbol: str, stock_info):
    """Build the existing detail response from FinMind daily-price data.

    ``None`` means FinMind did not provide usable data and must be replaced by
    the Yahoo Finance response.
    """
    token = get_finmind_token()
    if not token or not stock_info:
        return None

    price_rows = fetch_finmind_dataset(
        token,
        "TaiwanStockPrice",
        symbol,
        (date.today() - timedelta(days=45)).isoformat(),
    )
    if not price_rows:
        return None

    price_rows = sorted(
        (row for row in price_rows if row.get("date") and row.get("close") is not None),
        key=lambda row: row["date"],
    )
    if not price_rows:
        return None

    latest = price_rows[-1]
    close_price = safe_float(latest.get("close"))
    if close_price <= 0:
        return None

    previous_close = safe_float(price_rows[-2].get("close")) if len(price_rows) > 1 else 0.0
    dividend_rows = fetch_finmind_dataset(
        token,
        "TaiwanStockDividendResult",
        symbol,
        (date.today() - timedelta(days=365 * 5)).isoformat(),
    )
    dividends_info = []
    if dividend_rows:
        for row in dividend_rows:
            dividend_type = str(row.get("type", "")).lower()
            amount = safe_float(row.get("value"))
            # The result table contains several reference-price rows.  Only
            # cash-dividend entries represent a dividend paid to shareholders.
            if "cash" in dividend_type and amount > 0 and row.get("date"):
                dividends_info.append({"date": str(row["date"]), "amount": amount})
        dividends_info = sorted(dividends_info, key=lambda item: item["date"])[-3:]

    history_data = [
        {"date": str(row["date"]), "price": safe_float(row["close"])}
        for row in price_rows
    ]
    return {
        "symbol": str(symbol),
        "name": str(stock_info.name),
        "type": str(stock_info.type),
        "market": str(stock_info.market),
        "open": safe_float(latest.get("open")),
        "close": close_price,
        "previous_close": previous_close,
        "history": history_data,
        "dividends": dividends_info,
        "chart": {
            "labels": [item["date"] for item in history_data],
            "prices": [item["price"] for item in history_data],
        },
        "data_source": "FinMind",
    }


def get_yahoo_stock_detail(symbol: str):
    clean_sym = symbol.replace(".TW", "").replace(".TWO", "").strip()
    
    stock_info = twstock.codes.get(clean_sym)
    name = stock_info.name if stock_info else clean_sym
    stock_type = stock_info.type if stock_info else "股票"
    market = stock_info.market if stock_info else "未知"
    
    suffix = ".TW" if market == "上市" else ".TWO"
    
    history_data = []
    chart_labels = []
    chart_prices = []
    open_price = 0.0
    close_price = 0.0
    prev_close = 0.0
    dividends_info = []

    try:
        ticker = yf.Ticker(f"{clean_sym}{suffix}")
        
        # 安全取得 fast_info (相容字典與屬性存取方式)
        fast_info = getattr(ticker, 'fast_info', {})
        
        def get_fi(key, alt_key=None):
            try:
                if hasattr(fast_info, key):
                    val = getattr(fast_info, key)
                    if val is not None: return val
                if alt_key and hasattr(fast_info, alt_key):
                    val = getattr(fast_info, alt_key)
                    if val is not None: return val
                if isinstance(fast_info, dict):
                    if key in fast_info and fast_info[key] is not None:
                        return fast_info[key]
                    if alt_key and alt_key in fast_info and fast_info[alt_key] is not None:
                        return fast_info[alt_key]
            except Exception:
                pass
            return 0

        open_price = safe_float(get_fi('open', 'regularMarketOpen'))
        close_price = safe_float(get_fi('last_price', 'regularMarketPrice'))
        prev_close = safe_float(get_fi('previous_close', 'previousClose'))
        
        # 如果 fast_info 抓不到即時價，退回用 history 最後一筆補齊
        hist = ticker.history(period="1mo")
        if hist is not None and not hist.empty:
            if close_price == 0.0 and 'Close' in hist:
                close_price = safe_float(hist['Close'].iloc[-1])
            if open_price == 0.0 and 'Open' in hist:
                open_price = safe_float(hist['Open'].iloc[-1])
                
            for idx, row in hist.iterrows():
                date_str = str(idx)[:10]
                p = safe_float(row.get('Close', 0))
                history_data.append({"date": date_str, "price": p})
                chart_labels.append(date_str)
                chart_prices.append(p)

        # 抓取股利資訊
        try:
            divs = ticker.dividends
            if divs is not None and not divs.empty:
                recent_divs = divs.tail(3)
                for d_date, d_val in recent_divs.items():
                    d_str = str(d_date)[:10]
                    val = safe_float(d_val)
                    if val > 0:
                        dividends_info.append({
                            "date": d_str,
                            "amount": val
                        })
        except Exception:
            pass # 股利抓取失敗不影響主體渲染

    except Exception as e:
        print("=== STOCK DETAIL ERROR ===")
        print(traceback.format_exc())
        return {"error": str(e)}, 500

    return {
        "symbol": str(clean_sym),
        "name": str(name),
        "type": str(stock_type),
        "market": str(market),
        "open": open_price,
        "close": close_price,
        "previous_close": prev_close,
        "history": history_data,
        "dividends": dividends_info,
        "chart": {
            "labels": [str(l) for l in chart_labels],
            "prices": [safe_float(p) for p in chart_prices]
        },
        "data_source": "Yahoo Finance",
    }


@router.get("/api/stock-detail/{symbol}")
def get_stock_detail(symbol: str):
    clean_sym = symbol.replace(".TW", "").replace(".TWO", "").strip()
    finmind_detail = get_finmind_stock_detail(clean_sym, twstock.codes.get(clean_sym))
    if finmind_detail is not None:
        return finmind_detail

    # No token, non-Taiwan symbol, invalid token, request limit, connection
    # error, or missing FinMind data all retain the original behaviour.
    return get_yahoo_stock_detail(symbol)
