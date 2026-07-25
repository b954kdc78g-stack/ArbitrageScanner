"""Exchange manager for multi-exchange operations."""

from typing import Dict, List, Optional
from app.api.base_exchange import BaseExchange
from app.api.mexc import MEXCExchange
from app.api.bitget import BitgetExchange
from app.api.gateio import GateIOExchange
from app.api.kucoin import KuCoinExchange
from app.api.bybit import BybitExchange
from app.api.bingx import BingXExchange
from app.models.exchange_data import OrderBook, Ticker, WithdrawalInfo, DepositInfo, TradingFee
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class ExchangeManager:
    """Manager for handling multiple exchanges."""
    
    EXCHANGES = {
        "mexc": MEXCExchange,
        "bitget": BitgetExchange,
        "gateio": GateIOExchange,
        "kucoin": KuCoinExchange,
        "bybit": BybitExchange,
        "bingx": BingXExchange,
    }
    
    def __init__(self):
        self.exchanges: Dict[str, BaseExchange] = {}
        self._init_exchanges()
    
    def _init_exchanges(self) -> None:
        """Initialize all exchange clients."""
        for name, exchange_class in self.EXCHANGES.items():
            try:
                self.exchanges[name] = exchange_class()
                logger.info(f"Initialized {name} exchange")
            except Exception as e:
                logger.error(f"Failed to initialize {name} exchange: {e}")
    
    async def get_exchange(self, name: str) -> Optional[BaseExchange]:
        """Get exchange client by name."""
        return self.exchanges.get(name.lower())
    
    async def get_all_exchanges(self) -> Dict[str, BaseExchange]:
        """Get all exchange clients."""
        return self.exchanges
    
    async def get_ticker_from_all(self, symbol: str) -> Dict[str, Optional[Ticker]]:
        """Get ticker from all exchanges."""
        results = {}
        for name, exchange in self.exchanges.items():
            try:
                ticker = await exchange.get_ticker(symbol)
                results[name] = ticker
            except Exception as e:
                logger.error(f"Error getting ticker from {name} for {symbol}: {e}")
                results[name] = None
        return results
    
    async def get_order_book_from_all(self, symbol: str, limit: int = 20) -> Dict[str, Optional[OrderBook]]:
        """Get order book from all exchanges."""
        results = {}
        for name, exchange in self.exchanges.items():
            try:
                book = await exchange.get_order_book(symbol, limit)
                results[name] = book
            except Exception as e:
                logger.error(f"Error getting order book from {name} for {symbol}: {e}")
                results[name] = None
        return results
    
    async def get_common_pairs(self) -> Dict[str, List[str]]:
        """Get trading pairs from all exchanges."""
        results = {}
        for name, exchange in self.exchanges.items():
            try:
                pairs = await exchange.get_all_pairs()
                results[name] = pairs
            except Exception as e:
                logger.error(f"Error getting pairs from {name}: {e}")
                results[name] = []
        return results
    
    async def get_withdrawal_info_from_all(self, coin: str) -> Dict[str, Dict[str, WithdrawalInfo]]:
        """Get withdrawal info from all exchanges."""
        results = {}
        for name, exchange in self.exchanges.items():
            try:
                info = await exchange.get_withdrawal_info(coin)
                results[name] = info
            except Exception as e:
                logger.error(f"Error getting withdrawal info from {name} for {coin}: {e}")
                results[name] = {}
        return results
    
    async def get_deposit_info_from_all(self, coin: str) -> Dict[str, Dict[str, DepositInfo]]:
        """Get deposit info from all exchanges."""
        results = {}
        for name, exchange in self.exchanges.items():
            try:
                info = await exchange.get_deposit_info(coin)
                results[name] = info
            except Exception as e:
                logger.error(f"Error getting deposit info from {name} for {coin}: {e}")
                results[name] = {}
        return results
    
    async def get_trading_fees_from_all(self, symbol: str) -> Dict[str, Optional[TradingFee]]:
        """Get trading fees from all exchanges."""
        results = {}
        for name, exchange in self.exchanges.items():
            try:
                fee = await exchange.get_trading_fee(symbol)
                results[name] = fee
            except Exception as e:
                logger.error(f"Error getting trading fee from {name} for {symbol}: {e}")
                results[name] = None
        return results
    
    async def close_all(self) -> None:
        """Close all exchange connections."""
        for name, exchange in self.exchanges.items():
            try:
                await exchange.close()
                logger.info(f"Closed {name} exchange connection")
            except Exception as e:
                logger.error(f"Error closing {name} connection: {e}")
