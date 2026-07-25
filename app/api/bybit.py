"""Bybit Exchange API client."""

from typing import Dict, List, Optional
from datetime import datetime
from app.api.base_exchange import BaseExchange
from app.models.exchange_data import OrderBook, Ticker, WithdrawalInfo, DepositInfo, TradingFee
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class BybitExchange(BaseExchange):
    """Bybit exchange API client."""
    
    def __init__(self):
        super().__init__(
            name="Bybit",
            base_url="https://api.bybit.com",
            timeout=10
        )
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker data from Bybit."""
        try:
            data = await self._get("/v5/market/tickers", {"category": "spot", "symbol": symbol})
            
            if not data or data.get("retCode") != 0:
                return None
            
            ticker_list = data.get("result", {}).get("list", [])
            if not ticker_list:
                return None
            
            ticker_data = ticker_list[0]
            
            return Ticker(
                symbol=symbol,
                last_price=float(ticker_data.get("lastPrice", 0)),
                bid=float(ticker_data.get("bid1Price", 0)),
                ask=float(ticker_data.get("ask1Price", 0)),
                volume_24h=float(ticker_data.get("volume24h", 0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Bybit: Error getting ticker for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book from Bybit."""
        try:
            data = await self._get("/v5/market/orderbook", {"category": "spot", "symbol": symbol, "limit": limit})
            
            if not data or data.get("retCode") != 0:
                return None
            
            book_data = data.get("result", {})
            bids = [(float(p), float(q)) for p, q in book_data.get("b", [])]
            asks = [(float(p), float(q)) for p, q in book_data.get("a", [])]
            
            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Bybit: Error getting order book for {symbol}: {e}")
            return None
    
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs from Bybit."""
        try:
            data = await self._get("/v5/market/instruments-info", {"category": "spot"})
            
            if not data or data.get("retCode") != 0:
                return []
            
            symbols = [s["symbol"] for s in data.get("result", {}).get("list", []) if s.get("status") == "Trading"]
            return symbols
        except Exception as e:
            logger.error(f"Bybit: Error getting all pairs: {e}")
            return []
    
    async def get_withdrawal_info(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal information from Bybit."""
        try:
            result = {}
            data = await self._get("/v5/asset/coin/query-info", {"coin": coin})
            
            if not data or data.get("retCode") != 0:
                return result
            
            coin_list = data.get("result", {}).get("rows", [])
            if not coin_list:
                return result
            
            coin_data = coin_list[0]
            
            for chain in coin_data.get("chains", []):
                chain_name = chain.get("chainType", "unknown")
                result[chain_name] = WithdrawalInfo(
                    coin=coin,
                    network=chain_name,
                    min_withdrawal=float(chain.get("withdrawMin", 0)),
                    withdrawal_fee=float(chain.get("withdrawFee", 0)),
                    is_available=chain.get("withdrawStatus", "0") == "1"
                )
            
            return result
        except Exception as e:
            logger.error(f"Bybit: Error getting withdrawal info for {coin}: {e}")
            return {}
    
    async def get_deposit_info(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit information from Bybit."""
        try:
            result = {}
            data = await self._get("/v5/asset/coin/query-info", {"coin": coin})
            
            if not data or data.get("retCode") != 0:
                return result
            
            coin_list = data.get("result", {}).get("rows", [])
            if not coin_list:
                return result
            
            coin_data = coin_list[0]
            
            for chain in coin_data.get("chains", []):
                chain_name = chain.get("chainType", "unknown")
                result[chain_name] = DepositInfo(
                    coin=coin,
                    network=chain_name,
                    min_deposit=float(chain.get("depositMin", 0)),
                    deposit_fee=float(chain.get("depositFee", 0)),
                    is_available=chain.get("depositStatus", "0") == "1"
                )
            
            return result
        except Exception as e:
            logger.error(f"Bybit: Error getting deposit info for {coin}: {e}")
            return {}
    
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fees from Bybit."""
        try:
            # Bybit standard fees: 0.1% maker, 0.1% taker
            return TradingFee(
                symbol=symbol,
                maker_fee=0.001,
                taker_fee=0.001,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Bybit: Error getting trading fee for {symbol}: {e}")
            return None
