from fastapi import APIRouter
import twstock

router = APIRouter()

@router.get("/api/all-stocks")
def get_all_stocks():
    all_stocks = []
    for code, info in twstock.codes.items():
        if info.type in ["股票", "ETF"]:
            all_stocks.append(code)
    return all_stocks


@router.get("/api/search-stocks")
def search_stocks(keyword: str, limit: int = 12):
    """Find Taiwan stocks or ETFs by code or Chinese name for the desktop UI."""
    term = keyword.strip().lower()
    if not term:
        return []

    results = []
    for code, info in twstock.codes.items():
        if info.type not in ["股票", "ETF"]:
            continue
        if term in code.lower() or term in info.name.lower():
            results.append({"symbol": code, "name": info.name, "type": info.type})
            if len(results) >= max(1, min(limit, 30)):
                break
    return results
