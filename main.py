import logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from api_carousel import router as carousel_router
from api_quotes import router as quotes_router
from api_etf import router as etf_router
from api_finmind import router as finmind_router
from api_watchlist import router as watchlist_router
from api_news import router as news_router
from api_setting import router as setting_router
from api_backtest import router as backtest_router
from api_fundamentals import router as fundamentals_router
from db import init_db
import os
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

app = FastAPI()

# 初始化 SQLite 資料庫
init_db()

app.include_router(carousel_router)
app.include_router(quotes_router)
app.include_router(etf_router)
app.include_router(finmind_router)
app.include_router(watchlist_router)
app.include_router(news_router)
app.include_router(setting_router)
app.include_router(fundamentals_router)
app.include_router(backtest_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/", response_class=HTMLResponse)
def read_index():
    html_path = os.path.join(BASE_DIR, "dashboard.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()