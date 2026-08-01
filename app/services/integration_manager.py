"""Integration manager - orchestrates exchanges and arbitrage detection."""

from typing import Dict, List, Optional, Tuple
import asyncio
from app.api.exchange_factory import ExchangeFactory
from app.config.config_manager import ConfigurationManager, ExchangeConfig
from app.api.base_exchange_v2 import BaseExchange
from app.models.exchange_data import Ticker, ArbitrageOpportunity
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class IntegrationManager:
    """
    Orchestrates all exchanges and performs arbitrage detection.
    Manages lifecycle of exchange connections and data collection.
    """
    
    def __init__(self, config_path: str = "config/exchanges"):
        self.config_manager = ConfigurationManager(config_path)
        self.factory = ExchangeFactory(self.config_manager)
        self.active_exchanges: Dict[str, BaseExchange] = {}
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Initialize the integration manager."""
        try:
            # Initialize config manager
            await self.config_manager.initialize()
            logger.info("ConfigurationManager initialized")
            
            # Register all adapters
            self._register_adapters()
            
            return True
        except Exception as e:
            logger.error(f"Error initializing IntegrationManager: {e}")
            return False
    
    def _register_adapters(self) -> None:
        """Register all available exchange adapters."""
        from app.exchanges.binance import BinanceExchange
        from app.exchanges.kraken import KrakenExchange
        from app.exchanges.bybit import BybitExchange
        
        self.factory.register_adapter("binance", BinanceExchange)
        self.factory.register_adapter("kraken", KrakenExchange)
        self.factory.register_adapter("bybit", BybitExchange)
        
        logger.info(f"Registered adapters: {self.factory.get_registered_adapters()}")
    
    async def activate_exchange(
        self,
        exchange_name: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None
    ) -> bool:
        """
        Activate an exchange connection.
        
        Args:
            exchange_name: Name of the exchange
            api_key: Optional API key
            api_secret: Optional API secret
        
        Returns:
            True if activation was successful
        """
        try:
            if exchange_name in self.active_exchanges:
                logger.warning(f"{exchange_name} already active")
                return True
            
            exchange = await self.factory.create_exchange(
                exchange_name,
                api_key,
                api_secret
            )
            
            if not exchange:
                logger.error(f"Failed to create exchange: {exchange_name}")
                return False
            
            self.active_exchanges[exchange_name] = exchange
            logger.info(f"Activated exchange: {exchange_name}")
            return True
        except Exception as e:
            logger.error(f"Error activating {exchange_name}: {e}")
            return False
    
    async def deactivate_exchange(self, exchange_name: str) -> bool:
        """Deactivate an exchange connection."""
        if exchange_name not in self.active_exchanges:
            return False
        
        try:
            await self.factory.close_exchange(exchange_name)
            del self.active_exchanges[exchange_name]
            logger.info(f"Deactivated exchange: {exchange_name}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating {exchange_name}: {e}")
            return False
    
    async def activate_all_exchanges(self) -> Dict[str, bool]:
        """Activate all available exchanges."""
        results = {}
        available = self.factory.get_available_exchanges()
        
        for exchange_name in available:
            results[exchange_name] = await self.activate_exchange(exchange_name)
        
        return results
    
    async def get_ticker(self, exchange_name: str, symbol: str) -> Optional[Ticker]:
        """Get ticker from a specific exchange."""
        if exchange_name not in self.active_exchanges:
            logger.error(f"Exchange {exchange_name} not active")
            return None
        
        return await self.active_exchanges[exchange_name].get_ticker(symbol)
    
    async def get_tickers(self, symbol: str) -> Dict[str, Optional[Ticker]]:
        """Get tickers from all active exchanges for a symbol."""
        tasks = {
            exchange_name: self.get_ticker(exchange_name, symbol)
            for exchange_name in self.active_exchanges.keys()
        }
        
        results = {}
        for exchange_name, task in tasks.items():
            try:
                results[exchange_name] = await task
            except Exception as e:
                logger.error(f"Error getting ticker from {exchange_name}: {e}")
                results[exchange_name] = None
        
        return results
    
    async def find_arbitrage_opportunities(
        self,
        symbols: List[str],
        min_spread_percent: float = 1.0
    ) -> List[ArbitrageOpportunity]:
        """
        Find arbitrage opportunities across active exchanges.
        
        Args:
            symbols: List of symbols to check
            min_spread_percent: Minimum profitable spread percentage
        
        Returns:
            List of arbitrage opportunities found
        """
        opportunities = []
        
        for symbol in symbols:
            try:
                tickers = await self.get_tickers(symbol)
                
                # Filter out None values
                valid_tickers = {ex: ticker for ex, ticker in tickers.items() if ticker}
                
                if len(valid_tickers) < 2:
                    continue
                
                # Find buy and sell opportunities
                for buy_exchange, buy_ticker in valid_tickers.items():
                    for sell_exchange, sell_ticker in valid_tickers.items():
                        if buy_exchange == sell_exchange:
                            continue
                        
                        # Calculate spread
                        spread_percent = (
                            (sell_ticker.bid - buy_ticker.ask) / buy_ticker.ask * 100
                        )
                        
                        if spread_percent >= min_spread_percent:
                            opportunity = ArbitrageOpportunity(
                                symbol=symbol,
                                buy_exchange=buy_exchange,
                                sell_exchange=sell_exchange,
                                buy_price=buy_ticker.ask,
                                sell_price=sell_ticker.bid,
                                spread_percent=spread_percent,
                                timestamp=None
                            )
                            opportunities.append(opportunity)
            except Exception as e:
                logger.error(f"Error finding opportunities for {symbol}: {e}")
        
        return sorted(opportunities, key=lambda x: x.spread_percent, reverse=True)
    
    async def get_all_pairs(self) -> Dict[str, List[str]]:
        """Get all trading pairs from active exchanges."""
        results = {}
        
        tasks = {
            exchange_name: self.active_exchanges[exchange_name].get_all_pairs()
            for exchange_name in self.active_exchanges.keys()
        }
        
        for exchange_name, task in tasks.items():
            try:
                results[exchange_name] = await task
            except Exception as e:
                logger.error(f"Error getting pairs from {exchange_name}: {e}")
                results[exchange_name] = []
        
        return results
    
    def get_common_pairs(self) -> List[str]:
        """Get common trading pairs across all exchanges."""
        if not self.active_exchanges:
            return []
        
        # This is a placeholder - in production, you'd need to cache the results
        # from get_all_pairs() and find the intersection
        return []
    
    async def shutdown(self) -> None:
        """Shutdown all exchange connections."""
        await self.factory.close_all()
        self.active_exchanges.clear()
        await self.config_manager.close()
        logger.info("IntegrationManager shutdown complete")
