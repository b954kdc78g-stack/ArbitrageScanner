"""Bitget Exchange API client."""

from typing import Dict, List, Optional
from datetime import datetime
from app.api.base_exchange import BaseExchange
from app.models.exchange_data import OrderBook, Ticker, WithdrawalInfo, DepositInfo, TradingFee
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class BitgetExchange(BaseExchange):
    """Bitget exchange API client."""
    
    def __init__(self):
        super().__init__(
            name="Bitget",
            base_url="https://api.bitget.com",
            timeout=10
        )
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker data from Bitget."""
        try:
            # Bitget uses productId format like BTCUSDT
            data = await self._get(f"/spot/v1/public/ticker", {"symbol": symbol})
            if not data or data.get("code") != "00000":
                return None
            
            ticker_data = data.get("data", {})
            
            return Ticker(
                symbol=symbol,
                last_price=float(ticker_data.get("lastPr", 0)),
                bid=float(ticker_data.get("bidPr", 0)),
                ask=float(ticker_data.get("askPr", 0)),
                volume_24h=float(ticker_data.get("baseVolume", 0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Bitget: Error getting ticker for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book from Bitget."""
        try:
            data = await self._get(f"/spot/v1/public/depth", {"symbol": symbol, "limit": limit})
            if not data or data.get("code") != "00000":
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
            logger.error(f"Bitget: Error getting order book for {symbol}: {e}")
            return None
    
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs from Bitget."""
        try:
            data = await self._get("/spot/v1/public/products")
            if not data or data.get("code") != "00000":
                return []
            
            symbols = [s["symbol"] for s in data.get("data", []) if s.get("status") == "online"]
            return symbols
        except Exception as e:
            logger.error(f"Bitget: Error getting all pairs: {e}")
            return []
    
    async def get_withdrawal_info(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal information from Bitget."""
        try:
            result = {}
            data = await self._get("/spot/v1/public/coinInfo")
            
            if not data or data.get("code") != "00000":
                return result
            
            for coin_data in data.get("data", []):
                if coin_data.get("coin") == coin:
                    for chain in coin_data.get("chains", []):
                        chain_name = chain.get("chain", "unknown")
                        result[chain_name] = WithdrawalInfo(
                            coin=coin,
                            network=chain_name,
                            min_withdrawal=float(chain.get("minWithdraw", 0)),
                            withdrawal_fee=float(chain.get("withdrawFee", 0)),
                            is_available=chain.get("withdrawEnable", False) == "true"
                        )
            
            return result
        except Exception as e:
            logger.error(f"Bitget: Error getting withdrawal info for {coin}: {e}")
            return {}
    
    async def get_deposit_info(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit information from Bitget."""
        try:
            result = {}
            data = await self._get("/spot/v1/public/coinInfo")
            
            if not data or data.get("code") != "00000":
                return result
            
            for coin_data in data.get("data", []):
                if coin_data.get("coin") == coin:
                    for chain in coin_data.get("chains", []):
                        chain_name = chain.get("chain", "unknown")
                        result[chain_name] = DepositInfo(
                            coin=coin,
                            network=chain_name,
                            min_deposit=float(chain.get("minDeposit", 0)),
                            deposit_fee=float(chain.get("depositFee", 0)),
                            is_available=chain.get("depositEnable", False) == "true"
                        )
            
            return result
        except Exception as e:
            logger.error(f"Bitget: Error getting deposit info for {coin}: {e}")
            return {}
    
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fees from Bitget."""
        try:
            # Bitget standard fees: 0.1% maker, 0.1% taker
            return TradingFee(
                symbol=symbol,
                maker_fee=0.001,
                taker_fee=0.001,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Bitget: Error getting trading fee for {symbol}: {e}")
            return None
