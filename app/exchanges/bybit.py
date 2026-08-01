"""Bybit exchange adapter."""

from typing import Dict, List, Optional, Any
from app.api.base_exchange_v2 import BaseExchange
from app.config.config_manager import ExchangeConfig
from app.models.exchange_data import (
    Ticker, OrderBook, TradingFee, WithdrawalInfo, DepositInfo
)
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class BybitExchange(BaseExchange):
    """Bybit exchange adapter."""
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker from Bybit."""
        try:
            data = await self._request("GET", f"/v5/market/tickers?category=spot&symbol={symbol}")
            
            if not data.get("result", {}).get("list"):
                return None
            
            ticker = data["result"]["list"][0]
            
            return Ticker(
                exchange="bybit",
                symbol=symbol,
                bid=float(ticker.get("bid1Price", 0)),
                ask=float(ticker.get("ask1Price", 0)),
                last=float(ticker.get("lastPrice", 0)),
                volume_24h=float(ticker.get("volume24h", 0)),
                timestamp=int(ticker.get("time", 0)) / 1000
            )
        except Exception as e:
            logger.error(f"Error getting Bybit ticker for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book from Bybit."""
        try:
            data = await self._request("GET", f"/v5/market/orderbook?category=spot&symbol={symbol}&limit={limit}")
            
            if not data.get("result"):
                return None
            
            result = data["result"]
            
            bids = [[float(bid[0]), float(bid[1])] for bid in result.get("b", [])]
            asks = [[float(ask[0]), float(ask[1])] for ask in result.get("a", [])]
            
            return OrderBook(
                exchange="bybit",
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=int(result.get("ts", 0)) / 1000
            )
        except Exception as e:
            logger.error(f"Error getting Bybit order book for {symbol}: {e}")
            return None
    
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs from Bybit."""
        try:
            data = await self._request("GET", "/v5/market/instruments-info?category=spot")
            
            if not data.get("result", {}).get("list"):
                return []
            
            pairs = [item["symbol"] for item in data["result"]["list"] 
                    if item.get("status") == "Trading"]
            return pairs
        except Exception as e:
            logger.error(f"Error getting Bybit pairs: {e}")
            return []
    
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fee from Bybit."""
        try:
            if not self.api_key:
                # Use default fees
                maker_fee = self.config.trading_fees.get("maker", 0.001)
                taker_fee = self.config.trading_fees.get("taker", 0.001)
            else:
                data = await self._request("GET", "/v5/account/fee-rates?category=spot")
                
                if not data.get("result", {}).get("list"):
                    maker_fee = 0.001
                    taker_fee = 0.001
                else:
                    fee_data = data["result"]["list"][0]
                    maker_fee = float(fee_data.get("makerFeeRate", 0.001))
                    taker_fee = float(fee_data.get("takerFeeRate", 0.001))
            
            return TradingFee(
                exchange="bybit",
                symbol=symbol,
                maker=maker_fee,
                taker=taker_fee
            )
        except Exception as e:
            logger.error(f"Error getting Bybit fee for {symbol}: {e}")
            return None
    
    async def _get_withdrawal_info_impl(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal info from Bybit."""
        try:
            if not self.api_key:
                return {}
            
            data = await self._request("GET", f"/v5/asset/coin/query-info?coin={coin}")
            
            if not data.get("result", {}).get("rows"):
                return {}
            
            withdrawal_info = {}
            for row in data["result"]["rows"]:
                for chain in row.get("chains", []):
                    network_name = chain.get("chainType", "unknown")
                    withdrawal_info[network_name] = WithdrawalInfo(
                        coin=coin,
                        network=network_name,
                        withdrawal_fee=float(chain.get("withdrawFee", 0)),
                        min_withdrawal=float(chain.get("withdrawMin", 0)),
                        is_default=chain.get("isDefaultChain", False)
                    )
            
            return withdrawal_info
        except Exception as e:
            logger.error(f"Error getting Bybit withdrawal info for {coin}: {e}")
            return {}
    
    async def _get_deposit_info_impl(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit info from Bybit."""
        try:
            if not self.api_key:
                return {}
            
            data = await self._request("GET", f"/v5/asset/coin/query-info?coin={coin}")
            
            if not data.get("result", {}).get("rows"):
                return {}
            
            deposit_info = {}
            for row in data["result"]["rows"]:
                for chain in row.get("chains", []):
                    network_name = chain.get("chainType", "unknown")
                    deposit_info[network_name] = DepositInfo(
                        coin=coin,
                        network=network_name,
                        deposit_fee=0.0,  # Bybit typically doesn't charge deposit fees
                        min_deposit=float(chain.get("depositMin", 0)),
                        is_default=chain.get("isDefaultChain", False)
                    )
            
            return deposit_info
        except Exception as e:
            logger.error(f"Error getting Bybit deposit info for {coin}: {e}")
            return {}
