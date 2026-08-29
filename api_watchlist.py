from fastapi import APIRouter
from pydantic import BaseModel
from db import get_db_connection

router = APIRouter()

class WatchlistRequest(BaseModel, extra="allow"):
    symbols: str

@router.get("/api/watchlist")
def get_watchlist():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist")
    rows = cursor.fetchall()
    conn.close()
    return [row["symbol"] for row in rows]

@router.post("/api/watchlist")
def save_watchlist(data: WatchlistRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM watchlist")
    symbols = [s.strip() for s in data.symbols.split(",") if s.strip()]
    for sym in symbols:
        cursor.execute("INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (sym,))
    conn.commit()
    conn.close()
    return {"status": "success", "saved": symbols}
    