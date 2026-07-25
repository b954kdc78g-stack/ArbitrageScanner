"""Gate.io Exchange API client."""

from typing import Dict, List, Optional
from datetime import datetime
from app.api.base_exchange import BaseExchange
from app.models.exchange_data import OrderBook, Ticker, WithdrawalInfo, DepositInfo, TradingFee
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class GateIOExchange(BaseExchange):
    """Gate.io exchange API client."""
    
    def __init__(self):
        super().__init__(
            name="Gate.io",
            base_url="https://api.gateio.ws/api/v4",
            timeout=10
        )
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker data from Gate.io."""
        try:
            # Gate.io uses underscore format like BTC_USDT
            symbol_formatted = symbol.replace("USDT", "_USDT")
            data = await self._get(f"/spot/tickers", {"currency_pair": symbol_formatted})
            
            if not data or isinstance(data, dict) and data.get("label") == "invalid_param":
                return None
            
            if isinstance(data, list) and len(data) > 0:
                ticker_data = data[0]
            else:
                ticker_data = data
            
            return Ticker(
                symbol=symbol,
                last_price=float(ticker_data.get("last", 0)),
                bid=float(ticker_data.get("highest_bid", 0)),
                ask=float(ticker_data.get("lowest_ask", 0)),
                volume_24h=float(ticker_data.get("volume", 0)),
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Gate.io: Error getting ticker for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book from Gate.io."""
        try:
            symbol_formatted = symbol.replace("USDT", "_USDT")
            data = await self._get(f"/spot/order_book", {"currency_pair": symbol_formatted, "limit": limit})
            
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
            logger.error(f"Gate.io: Error getting order book for {symbol}: {e}")
            return None
    
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs from Gate.io."""
        try:
            data = await self._get("/spot/currency_pairs")
            
            if not data:
                return []
            
            symbols = [s["id"].replace("_", "") for s in data if s.get("trade_status") == "tradable"]
            return symbols
        except Exception as e:
            logger.error(f"Gate.io: Error getting all pairs: {e}")
            return []
    
    async def get_withdrawal_info(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal information from Gate.io."""
        try:
            result = {}
            data = await self._get(f"/wallet/currency_chains/{coin}")
            
            if not data or isinstance(data, dict) and data.get("label"):
                return result
            
            if isinstance(data, dict):
                data = [data]
            
            for chain_data in data:
                chain_name = chain_data.get("chain", "unknown")
                result[chain_name] = WithdrawalInfo(
                    coin=coin,
                    network=chain_name,
                    min_withdrawal=float(chain_data.get("withdraw_min", 0)),
                    withdrawal_fee=float(chain_data.get("withdraw_fee", 0)),
                    is_available=chain_data.get("withdraw_disabled", True) == False
                )
            
            return result
        except Exception as e:
            logger.error(f"Gate.io: Error getting withdrawal info for {coin}: {e}")
            return {}
    
    async def get_deposit_info(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit information from Gate.io."""
        try:
            result = {}
            data = await self._get(f"/wallet/currency_chains/{coin}")
            
            if not data or isinstance(data, dict) and data.get("label"):
                return result
            
            if isinstance(data, dict):
                data = [data]
            
            for chain_data in data:
                chain_name = chain_data.get("chain", "unknown")
                result[chain_name] = DepositInfo(
                    coin=coin,
                    network=chain_name,
                    min_deposit=float(chain_data.get("deposit_min", 0)),
                    deposit_fee=float(chain_data.get("deposit_fee", 0)),
                    is_available=chain_data.get("deposit_disabled", True) == False
                )
            
            return result
        except Exception as e:
            logger.error(f"Gate.io: Error getting deposit info for {coin}: {e}")
            return {}
    
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fees from Gate.io."""
        try:
            # Gate.io standard fees: 0.18% maker, 0.18% taker
            return TradingFee(
                symbol=symbol,
                maker_fee=0.0018,
                taker_fee=0.0018,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Gate.io: Error getting trading fee for {symbol}: {e}")
            return None
