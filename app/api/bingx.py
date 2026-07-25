"""BingX Exchange API client."""

from typing import Dict, List, Optional
from datetime import datetime
from app.api.base_exchange import BaseExchange
from app.models.exchange_data import OrderBook, Ticker, WithdrawalInfo, DepositInfo, TradingFee
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class BingXExchange(BaseExchange):
    """BingX exchange API client."""
    
    def __init__(self):
        super().__init__(
            name="BingX",
            base_url="https://open-api.bingx.com",
            timeout=10
        )
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker data from BingX."""
        try:
            data = await self._get("/openApi/spot/v1/ticker/24hr", {"symbol": symbol})
            
            if not data or data.get("code") != "0":
                return None
            
            ticker_data = data.get("data", {})
            
            return Ticker(
                symbol=symbol,
                last_price=float(ticker_data.get("lastPrice", 0)),
                bid=float(ticker_data.get("bidPrice", 0)),
                ask=float(ticker_data.get("askPrice", 0)),
                volume_24h=float(ticker_data.get("volume", 0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"BingX: Error getting ticker for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book from BingX."""
        try:
            data = await self._get("/openApi/spot/v1/depth", {"symbol": symbol, "limit": limit})
            
            if not data or data.get("code") != "0":
                return None
            
            book_data = data.get("data", {})
            bids = [(float(p), float(q)) for p, q in book_data.get("bids", [])]
            asks = [(float(p), float(q)) for p, q in book_data.get("asks", [])]
            
            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"BingX: Error getting order book for {symbol}: {e}")
            return None
    
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs from BingX."""
        try:
            data = await self._get("/openApi/spot/v1/public/products")
            
            if not data or data.get("code") != "0":
                return []
            
            symbols = [s["symbol"] for s in data.get("data", []) if s.get("status") == "1"]
            return symbols
        except Exception as e:
            logger.error(f"BingX: Error getting all pairs: {e}")
            return []
    
    async def get_withdrawal_info(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal information from BingX."""
        try:
            result = {}
            data = await self._get("/openApi/wallets/v1/capital/config/getall")
            
            if not data or data.get("code") != "0":
                return result
            
            for coin_data in data.get("data", []):
                if coin_data.get("coin") == coin:
                    for network in coin_data.get("networkList", []):
                        network_name = network.get("network", "unknown")
                        result[network_name] = WithdrawalInfo(
                            coin=coin,
                            network=network_name,
                            min_withdrawal=float(network.get("withdrawMin", 0)),
                            withdrawal_fee=float(network.get("withdrawFee", 0)),
                            is_available=network.get("withdrawEnable", False)
                        )
            
            return result
        except Exception as e:
            logger.error(f"BingX: Error getting withdrawal info for {coin}: {e}")
            return {}
    
    async def get_deposit_info(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit information from BingX."""
        try:
            result = {}
            data = await self._get("/openApi/wallets/v1/capital/config/getall")
            
            if not data or data.get("code") != "0":
                return result
            
            for coin_data in data.get("data", []):
                if coin_data.get("coin") == coin:
                    for network in coin_data.get("networkList", []):
                        network_name = network.get("network", "unknown")
                        result[network_name] = DepositInfo(
                            coin=coin,
                            network=network_name,
                            min_deposit=float(network.get("depositMin", 0)),
                            deposit_fee=float(network.get("depositFee", 0)),
                            is_available=network.get("depositEnable", False)
                        )
            
            return result
        except Exception as e:
            logger.error(f"BingX: Error getting deposit info for {coin}: {e}")
            return {}
    
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fees from BingX."""
        try:
            # BingX standard fees: 0.1% maker, 0.1% taker
            return TradingFee(
                symbol=symbol,
                maker_fee=0.001,
                taker_fee=0.001,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"BingX: Error getting trading fee for {symbol}: {e}")
            return None
