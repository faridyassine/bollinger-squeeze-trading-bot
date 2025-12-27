"""Market data package."""
from .market_data import MarketDataProvider, get_data_provider

# Lazy imports to avoid loading dependencies unless needed
def __getattr__(name):
    if name == 'YahooFinanceProvider':
        from .yahoo_finance import YahooFinanceProvider
        return YahooFinanceProvider
    elif name == 'AlpacaDataProvider':
        from .alpaca import AlpacaDataProvider
        return AlpacaDataProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['MarketDataProvider', 'YahooFinanceProvider', 'AlpacaDataProvider', 'get_data_provider']
