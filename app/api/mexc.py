"""MEXC Exchange API client."""

from typing import Dict, List, Optional
from datetime import datetime
from app.api.base_exchange import BaseExchange
from app.models.exchange_data import OrderBook, Ticker, WithdrawalInfo, DepositInfo, TradingFee
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class MEXCExchange(BaseExchange):
    """MEXC exchange API client."""
    
    def __init__(self):
        super().__init__(
            name="MEXC",
            base_url="https://api.mexc.com",
            timeout=10
        )
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker data from MEXC."""
        try:
            data = await self._get("/api/v3/ticker/24hr", {"symbol": symbol})
            if not data:
                return None
            
            return Ticker(
                symbol=symbol,
                last_price=float(data.get("lastPrice", 0)),
                bid=float(data.get("bidPrice", 0)),
                ask=float(data.get("askPrice", 0)),
                volume_24h=float(data.get("volume", 0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"MEXC: Error getting ticker for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book from MEXC."""
        try:
            data = await self._get("/api/v3/depth", {"symbol": symbol, "limit": limit})
            if not data:
                return None
            
            bids = [(float(p), float(q)) for p, q in data.get("bids", [])]
            asks = [(float(p), float(q)) for p, q in data.get("asks", [])]
            
            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"MEXC: Error getting order book for {symbol}: {e}")
            return None
    
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs from MEXC."""
        try:
            data = await self._get("/api/v3/exchangeInfo")
            if not data:
                return []
            
            symbols = [s["symbol"] for s in data.get("symbols", []) if s.get("status") == "TRADING"]
            return symbols
        except Exception as e:
            logger.error(f"MEXC: Error getting all pairs: {e}")
            return []
    
    async def get_withdrawal_info(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal information from MEXC."""
        try:
            # MEXC requires authentication for withdrawal info
            # Using public endpoint for basic info
            result = {}
            data = await self._get("/api/v3/capital/config/getall")
            
            if not data:
                return result
            
            for coin_data in data:
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
            logger.error(f"MEXC: Error getting withdrawal info for {coin}: {e}")
            return {}
    
    async def get_deposit_info(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit information from MEXC."""
        try:
            result = {}
            data = await self._get("/api/v3/capital/config/getall")
            
            if not data:
                return result
            
            for coin_data in data:
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
            logger.error(f"MEXC: Error getting deposit info for {coin}: {e}")
            return {}
    
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fees from MEXC."""
        try:
            # MEXC has standard fees, typically 0.2% maker and 0.2% taker for default
            data = await self._get("/api/v3/account/tradeFee", {"symbol": symbol})
            
            if not data:
                # Return default fees
                return TradingFee(
                    symbol=symbol,
                    maker_fee=0.002,
                    taker_fee=0.002,
                    timestamp=datetime.now()
                )
            
            return TradingFee(
                symbol=symbol,
                maker_fee=float(data.get("makerCommission", 0.002)) / 10000,
                taker_fee=float(data.get("takerCommission", 0.002)) / 10000,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"MEXC: Error getting trading fee for {symbol}: {e}")
            return None
