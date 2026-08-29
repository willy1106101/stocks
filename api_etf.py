from fastapi import APIRouter
import pandas as pd
import yfinance as yf
import twstock

router = APIRouter()

def fetch_etf_holdings(etf_id: str) -> pd.DataFrame:
    clean_id = etf_id.replace(".TW", "").replace(".TWO", "").strip()
    
    try:
        ticker = yf.Ticker(f"{clean_id}.TW")
        holders = ticker.funds_data.top_holdings
        if holders is not None and not holders.empty:
            df = holders.reset_index()
            if len(df.columns) >= 3:
                df.columns = ["symbol", "name", "weight"]
            else:
                df.columns = ["symbol", "weight"]
                df["name"] = df["symbol"]
            
            cleaned_symbols = []
            cleaned_names = []
            for sym in df['symbol']:
                s = str(sym).replace(".TW", "").replace(".TWO", "").strip()
                cleaned_symbols.append(s)
                if s in twstock.codes:
                    cleaned_names.append(twstock.codes[s].name)
                else:
                    match_row = df[df['symbol'] == sym]
                    orig_name = match_row['name'].values[0] if not match_row.empty else s
                    cleaned_names.append(orig_name)

            df['symbol'] = cleaned_symbols
            df['name'] = cleaned_names
            df['weight'] = pd.to_numeric(df['weight'], errors='coerce') * 100
            df = df.dropna(subset=["symbol", "weight"])
            if not df.empty:
                return df
    except Exception:
        pass

    return pd.DataFrame(columns=["symbol", "name", "weight"])

@router.get("/api/etf-overlap")
def analyze_overlap(etf1: str, etf2: str):
    df1 = fetch_etf_holdings(etf1)
    df2 = fetch_etf_holdings(etf2)

    if df1.empty or df2.empty:
        return []

    overlap = pd.merge(
        df1, df2, 
        on="symbol", 
        suffixes=(f'_{etf1}', f'_{etf2}')
    )
    
    if f'name_{etf1}' in overlap.columns:
        overlap['name'] = overlap[f'name_{etf1}']
    elif 'name_x' in overlap.columns:
        overlap['name'] = overlap['name_x']
    elif 'name' not in overlap.columns:
        overlap['name'] = overlap['symbol']

    weight_col1 = f'weight_{etf1}'
    weight_col2 = f'weight_{etf2}'
    if weight_col1 in overlap.columns:
        overlap[weight_col1] = overlap[weight_col1].round(2)
    if weight_col2 in overlap.columns:
        overlap[weight_col2] = overlap[weight_col2].round(2)

    overlap = overlap.sort_values(by=weight_col1, ascending=False)
    return overlap.to_dict(orient="records")