"""KuCoin Exchange API client."""

from typing import Dict, List, Optional
from datetime import datetime
from app.api.base_exchange import BaseExchange
from app.models.exchange_data import OrderBook, Ticker, WithdrawalInfo, DepositInfo, TradingFee
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class KuCoinExchange(BaseExchange):
    """KuCoin exchange API client."""
    
    def __init__(self):
        super().__init__(
            name="KuCoin",
            base_url="https://api.kucoin.com",
            timeout=10
        )
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker data from KuCoin."""
        try:
            data = await self._get(f"/api/v1/market/stats", {"symbol": symbol})
            
            if not data or not data.get("success"):
                return None
            
            ticker_data = data.get("data", {})
            
            return Ticker(
                symbol=symbol,
                last_price=float(ticker_data.get("last", 0)),
                bid=float(ticker_data.get("buy", 0)),
                ask=float(ticker_data.get("sell", 0)),
                volume_24h=float(ticker_data.get("volValue", 0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"KuCoin: Error getting ticker for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book from KuCoin."""
        try:
            data = await self._get(f"/api/v1/market/orderbook/level1", {"symbol": symbol})
            
            if not data or not data.get("success"):
                return None
            
            book_data = data.get("data", {})
            
            # KuCoin level1 only gives top bid/ask, need to fetch level2 for full book
            data_l2 = await self._get(f"/api/v1/market/orderbook/level2_20", {"symbol": symbol})
            
            if data_l2 and data_l2.get("success"):
                book_data = data_l2.get("data", {})
                bids = [(float(p), float(q)) for p, q in book_data.get("bids", [])]
                asks = [(float(p), float(q)) for p, q in book_data.get("asks", [])]
            else:
                bids = [[float(book_data.get("bestBid", 0)), 0]]
                asks = [[float(book_data.get("bestAsk", 0)), 0]]
            
            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"KuCoin: Error getting order book for {symbol}: {e}")
            return None
    
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs from KuCoin."""
        try:
            data = await self._get("/api/v1/symbols")
            
            if not data or not data.get("success"):
                return []
            
            symbols = [s["name"] for s in data.get("data", []) if s.get("enableTrading")]
            return symbols
        except Exception as e:
            logger.error(f"KuCoin: Error getting all pairs: {e}")
            return []
    
    async def get_withdrawal_info(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal information from KuCoin."""
        try:
            result = {}
            data = await self._get(f"/api/v1/currencies/{coin}")
            
            if not data or not data.get("success"):
                return result
            
            coin_data = data.get("data", {})
            
            for chain_data in coin_data.get("chains", []):
                chain_name = chain_data.get("chainName", "unknown")
                result[chain_name] = WithdrawalInfo(
                    coin=coin,
                    network=chain_name,
                    min_withdrawal=float(chain_data.get("withdrawalMinSize", 0)),
                    withdrawal_fee=float(chain_data.get("withdrawalMinFee", 0)),
                    is_available=chain_data.get("isWithdrawEnabled", False)
                )
            
            return result
        except Exception as e:
            logger.error(f"KuCoin: Error getting withdrawal info for {coin}: {e}")
            return {}
    
    async def get_deposit_info(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit information from KuCoin."""
        try:
            result = {}
            data = await self._get(f"/api/v1/currencies/{coin}")
            
            if not data or not data.get("success"):
                return result
            
            coin_data = data.get("data", {})
            
            for chain_data in coin_data.get("chains", []):
                chain_name = chain_data.get("chainName", "unknown")
                result[chain_name] = DepositInfo(
                    coin=coin,
                    network=chain_name,
                    min_deposit=float(chain_data.get("depositMinSize", 0)),
                    deposit_fee=float(chain_data.get("depositMinFee", 0)),
                    is_available=chain_data.get("isDepositEnabled", False)
                )
            
            return result
        except Exception as e:
            logger.error(f"KuCoin: Error getting deposit info for {coin}: {e}")
            return {}
    
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fees from KuCoin."""
        try:
            # KuCoin standard fees: 0.1% maker, 0.1% taker
            return TradingFee(
                symbol=symbol,
                maker_fee=0.001,
                taker_fee=0.001,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"KuCoin: Error getting trading fee for {symbol}: {e}")
            return None
