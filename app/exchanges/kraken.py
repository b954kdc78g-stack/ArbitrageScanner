"""Kraken exchange adapter."""

from typing import Dict, List, Optional, Any
from app.api.base_exchange_v2 import BaseExchange
from app.config.config_manager import ExchangeConfig
from app.models.exchange_data import (
    Ticker, OrderBook, TradingFee, WithdrawalInfo, DepositInfo
)
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class KrakenExchange(BaseExchange):
    """Kraken exchange adapter."""
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker from Kraken."""
        try:
            # Kraken uses different symbol format (XXBTZUSD instead of BTCUSD)
            kraken_symbol = self._convert_symbol_to_kraken(symbol)
            data = await self._request("GET", f"/Ticker?pair={kraken_symbol}")
            
            if not data.get("result"):
                return None
            
            ticker_data = list(data["result"].values())[0]
            
            return Ticker(
                exchange="kraken",
                symbol=symbol,
                bid=float(ticker_data["b"][0]),
                ask=float(ticker_data["a"][0]),
                last=float(ticker_data["c"][0]),
                volume_24h=float(ticker_data["v"][1]),
                timestamp=None
            )
        except Exception as e:
            logger.error(f"Error getting Kraken ticker for {symbol}: {e}")
            return None
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book from Kraken."""
        try:
            kraken_symbol = self._convert_symbol_to_kraken(symbol)
            data = await self._request("GET", f"/Depth?pair={kraken_symbol}&count={limit}")
            
            if not data.get("result"):
                return None
            
            book_data = list(data["result"].values())[0]
            
            bids = [[float(bid[0]), float(bid[1])] for bid in book_data.get("bids", [])]
            asks = [[float(ask[0]), float(ask[1])] for ask in book_data.get("asks", [])]
            
            return OrderBook(
                exchange="kraken",
                symbol=symbol,
                bids=bids,
                asks=asks,
                timestamp=None
            )
        except Exception as e:
            logger.error(f"Error getting Kraken order book for {symbol}: {e}")
            return None
    
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs from Kraken."""
        try:
            data = await self._request("GET", "/AssetPairs")
            
            if not data.get("result"):
                return []
            
            pairs = [pair_name for pair_name, pair_data in data["result"].items() 
                    if pair_data.get("status") == "online"]
            return pairs
        except Exception as e:
            logger.error(f"Error getting Kraken pairs: {e}")
            return []
    
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fee from Kraken."""
        try:
            if not self.api_key:
                # Use default fees
                maker_fee = self.config.trading_fees.get("maker", 0.0016)
                taker_fee = self.config.trading_fees.get("taker", 0.0026)
            else:
                data = await self._request("GET", "/TradeVolume")
                
                if not data.get("result"):
                    maker_fee = 0.0016
                    taker_fee = 0.0026
                else:
                    fees = data["result"].get("fees", {})
                    maker_fee = float(list(fees.values())[0].get("maker", 0.0016))
                    taker_fee = float(list(fees.values())[0].get("taker", 0.0026))
            
            return TradingFee(
                exchange="kraken",
                symbol=symbol,
                maker=maker_fee,
                taker=taker_fee
            )
        except Exception as e:
            logger.error(f"Error getting Kraken fee for {symbol}: {e}")
            return None
    
    async def _get_withdrawal_info_impl(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal info from Kraken."""
        try:
            if not self.api_key:
                return {}
            
            data = await self._request("GET", "/WithdrawInfo?asset=ALL")
            
            if not data.get("result"):
                return {}
            
            withdrawal_info = {}
            for method, info in data["result"].items():
                if coin.lower() in method.lower():
                    withdrawal_info[method] = WithdrawalInfo(
                        coin=coin,
                        network=method,
                        withdrawal_fee=float(info.get("fee", 0)),
                        min_withdrawal=float(info.get("minAmount", 0)),
                        is_default=True
                    )
            
            return withdrawal_info
        except Exception as e:
            logger.error(f"Error getting Kraken withdrawal info for {coin}: {e}")
            return {}
    
    async def _get_deposit_info_impl(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit info from Kraken."""
        try:
            if not self.api_key:
                return {}
            
            data = await self._request("GET", "/DepositMethods?asset=ALL")
            
            if not data.get("result"):
                return {}
            
            deposit_info = {}
            for method, info in data["result"].items():
                if coin.lower() in method.lower():
                    deposit_info[method] = DepositInfo(
                        coin=coin,
                        network=method,
                        deposit_fee=0.0,  # Kraken typically doesn't charge deposit fees
                        min_deposit=float(info.get("minAmount", 0)),
                        is_default=True
                    )
            
            return deposit_info
        except Exception as e:
            logger.error(f"Error getting Kraken deposit info for {coin}: {e}")
            return {}
    
    def _convert_symbol_to_kraken(self, symbol: str) -> str:
        """Convert standard symbol to Kraken format."""
        # Simple conversion - in production, use a mapping table
        symbol_map = {
            "BTCUSD": "XXBTZUSD",
            "ETHUSD": "XETHUSD",
            "USDTUSD": "USDTZUSD",
        }
        return symbol_map.get(symbol, symbol)
