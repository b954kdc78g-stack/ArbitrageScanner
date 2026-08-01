"""Binance exchange adapter."""

from typing import Dict, List, Optional, Any
from app.api.base_exchange_v2 import BaseExchange
from app.config.config_manager import ExchangeConfig
from app.models.exchange_data import (
    Ticker, OrderBook, TradingFee, WithdrawalInfo, DepositInfo
)
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class BinanceExchange(BaseExchange):
    """Binance exchange adapter."""
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker from Binance."""
        try:
            data = await self._request("GET", f"/ticker/24hr?symbol={symbol}")
            
            return Ticker(
                exchange="binance",
                symbol=symbol,
                bid=float(data.get("bidPrice", 0)),
                ask=float(data.get("askPrice", 0)),
                last=float(data.get("lastPrice", 0)),
                volume_24h=float(data.get("volume", 0)),
                timestamp=int(data.get("time", 0)) / 1000
            )
        except Exception as e:
            logger.error(f"Error getting Binance ticker for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book from Binance."""
        try:
            data = await self._request("GET", f"/depth?symbol={symbol}&limit={limit}")
            
            bids = [[float(bid[0]), float(bid[1])] for bid in data.get("bids", [])]
            asks = [[float(ask[0]), float(ask[1])] for ask in data.get("asks", [])]
            
            return OrderBook(
                exchange="binance",
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=int(data.get("E", 0)) / 1000
            )
        except Exception as e:
            logger.error(f"Error getting Binance order book for {symbol}: {e}")
            return None
    
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs from Binance."""
        try:
            data = await self._request("GET", "/exchangeInfo")
            pairs = [s["symbol"] for s in data.get("symbols", []) if s.get("status") == "TRADING"]
            return pairs
        except Exception as e:
            logger.error(f"Error getting Binance pairs: {e}")
            return []
    
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fee from Binance."""
        try:
            # Binance requires API key for detailed fee info
            if not self.api_key:
                # Use default fees
                maker_fee = self.config.trading_fees.get("maker", 0.001)
                taker_fee = self.config.trading_fees.get("taker", 0.001)
            else:
                data = await self._request("GET", "/account")
                maker_fee = float(data.get("makerCommission", 10)) / 10000
                taker_fee = float(data.get("takerCommission", 10)) / 10000
            
            return TradingFee(
                exchange="binance",
                symbol=symbol,
                maker=maker_fee,
                taker=taker_fee
            )
        except Exception as e:
            logger.error(f"Error getting Binance fee for {symbol}: {e}")
            return None
    
    async def _get_withdrawal_info_impl(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal info from Binance."""
        try:
            if not self.api_key:
                return {}
            
            data = await self._request("GET", f"/capital/config/getall")
            
            withdrawal_info = {}
            for coin_data in data:
                if coin_data.get("coin") == coin:
                    for network in coin_data.get("networkList", []):
                        network_name = network.get("network", "unknown")
                        withdrawal_info[network_name] = WithdrawalInfo(
                            coin=coin,
                            network=network_name,
                            withdrawal_fee=float(network.get("withdrawFee", 0)),
                            min_withdrawal=float(network.get("withdrawMin", 0)),
                            is_default=network.get("isDefault", False)
                        )
            
            return withdrawal_info
        except Exception as e:
            logger.error(f"Error getting Binance withdrawal info for {coin}: {e}")
            return {}
    
    async def _get_deposit_info_impl(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit info from Binance."""
        try:
            if not self.api_key:
                return {}
            
            data = await self._request("GET", f"/capital/config/getall")
            
            deposit_info = {}
            for coin_data in data:
                if coin_data.get("coin") == coin:
                    for network in coin_data.get("networkList", []):
                        network_name = network.get("network", "unknown")
                        deposit_info[network_name] = DepositInfo(
                            coin=coin,
                            network=network_name,
                            deposit_fee=float(network.get("depositDesc", "0").replace("Free", "0")),
                            min_deposit=0,
                            is_default=network.get("isDefault", False)
                        )
            
            return deposit_info
        except Exception as e:
            logger.error(f"Error getting Binance deposit info for {coin}: {e}")
            return {}
