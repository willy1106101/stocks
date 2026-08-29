"""Python methods exposed only to the embedded pywebview window.

This module deliberately contains no HTTP server.  pywebview serializes the
return values of these methods directly back to JavaScript in the desktop
window, so the application does not need to listen on a TCP port.
"""

from api_backtest import get_backtest_data
from api_carousel import get_all_stocks, search_stocks
from api_etf import analyze_overlap
from api_finmind import get_stock_detail
from api_fundamentals import get_fundamentals
from api_quotes import get_batch_quotes
from api_setting import get_setting, save_setting
from api_watchlist import get_watchlist, save_watchlist


class DesktopApi:
    """The private API available as ``window.pywebview.api``."""

    def all_stocks(self):
        return get_all_stocks()

    def search_stocks(self, keyword: str):
        return search_stocks(keyword)

    def quotes(self, symbols: str = ""):
        return get_batch_quotes(symbols)

    def watchlist(self):
        return get_watchlist()

    def save_watchlist(self, symbols: str):
        # The original FastAPI route accepts a Pydantic model.  Its validated
        # constructor keeps the same input validation when called locally.
        from api_watchlist import WatchlistRequest
        return save_watchlist(WatchlistRequest(symbols=symbols))

    def setting(self, key: str):
        return get_setting(key)

    def save_setting(self, key: str, value: str):
        from api_setting import SettingItem
        return save_setting(SettingItem(key=key, value=value))

    def fundamentals(self, symbols: str):
        return get_fundamentals(symbols)

    def stock_detail(self, symbol: str):
        result = get_stock_detail(symbol)
        # Keep errors JSON-serializable; FastAPI normally converts this tuple
        # into an HTTP response for us.
        if isinstance(result, tuple):
            body, _status_code = result
            return body
        return result

    def etf_overlap(self, etf1: str, etf2: str):
        return analyze_overlap(etf1, etf2)

    def backtest(self, symbols: str, period: str = "1y"):
        return get_backtest_data(symbols, period)
