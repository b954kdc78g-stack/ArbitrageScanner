"""Arbitrage scanner service."""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from app.api.manager import ExchangeManager
from app.models.exchange_data import Ticker, OrderBook, ArbitrageOpportunity
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class ArbitrageScanner:
    """Service for scanning arbitrage opportunities."""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.manager = exchange_manager
        self.opportunities: List[ArbitrageOpportunity] = []
        self.scan_history: Dict[str, List[ArbitrageOpportunity]] = {}
    
    async def scan_all_pairs(self, min_profit_percent: float = 0.5) -> List[ArbitrageOpportunity]:
        """Scan all pairs across all exchanges for arbitrage opportunities."""
        logger.info(f"Starting arbitrage scan with min profit: {min_profit_percent}%")
        
        opportunities = []
        pairs_data = await self.manager.get_common_pairs()
        
        # Find common pairs across exchanges
        all_pairs = set()
        for pairs in pairs_data.values():
            all_pairs.update(pairs)
        
        logger.info(f"Found {len(all_pairs)} total pairs across exchanges")
        
        # Scan pairs in batches
        batch_size = 50
        pairs_list = list(all_pairs)
        
        for i in range(0, len(pairs_list), batch_size):
            batch = pairs_list[i:i+batch_size]
            batch_opps = await asyncio.gather(
                *[self._scan_pair(pair, min_profit_percent) for pair in batch]
            )
            opportunities.extend([opp for opp in batch_opps if opp])
        
        self.opportunities = opportunities
        logger.info(f"Scan completed. Found {len(opportunities)} opportunities")
        
        return opportunities
    
    async def _scan_pair(self, symbol: str, min_profit_percent: float) -> Optional[ArbitrageOpportunity]:
        """Scan a single pair for arbitrage opportunities."""
        try:
            tickers = await self.manager.get_ticker_from_all(symbol)
            
            # Filter valid tickers
            valid_tickers = {
                name: ticker for name, ticker in tickers.items()
                if ticker and ticker.last_price > 0
            }
            
            if len(valid_tickers) < 2:
                return None
            
            # Find best buy and sell prices
            buy_exchange = min(valid_tickers.items(), key=lambda x: x[1].last_price)
            sell_exchange = max(valid_tickers.items(), key=lambda x: x[1].last_price)
            
            buy_price = buy_exchange[1].last_price
            sell_price = sell_exchange[1].last_price
            
            profit_percent = ((sell_price - buy_price) / buy_price) * 100
            
            if profit_percent >= min_profit_percent:
                opportunity = ArbitrageOpportunity(
                    symbol=symbol,
                    buy_exchange=buy_exchange[0],
                    sell_exchange=sell_exchange[0],
                    buy_price=buy_price,
                    sell_price=sell_price,
                    profit_percent=profit_percent,
                    timestamp=datetime.now()
                )
                return opportunity
            
            return None
        except Exception as e:
            logger.error(f"Error scanning pair {symbol}: {e}")
            return None
    
    async def scan_specific_pairs(self, symbols: List[str], min_profit_percent: float = 0.5) -> List[ArbitrageOpportunity]:
        """Scan specific pairs for arbitrage opportunities."""
        logger.info(f"Scanning {len(symbols)} specific pairs")
        
        opportunities = await asyncio.gather(
            *[self._scan_pair(symbol, min_profit_percent) for symbol in symbols]
        )
        
        opportunities = [opp for opp in opportunities if opp]
        logger.info(f"Found {len(opportunities)} opportunities in specific pairs")
        
        return opportunities
    
    async def monitor_pair(self, symbol: str, interval: int = 60) -> None:
        """Monitor a specific pair continuously."""
        logger.info(f"Starting to monitor {symbol} with {interval}s interval")
        
        while True:
            try:
                opportunities = await self.scan_specific_pairs([symbol])
                if opportunities:
                    self.opportunities.extend(opportunities)
                    logger.info(f"Found opportunity for {symbol}: {opportunities[0]}")
                
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")
                await asyncio.sleep(interval)
    
    def get_best_opportunities(self, limit: int = 10) -> List[ArbitrageOpportunity]:
        """Get best opportunities sorted by profit percentage."""
        sorted_opps = sorted(
            self.opportunities,
            key=lambda x: x.profit_percent,
            reverse=True
        )
        return sorted_opps[:limit]
    
    def get_opportunities_by_exchange_pair(self, buy_exchange: str, sell_exchange: str) -> List[ArbitrageOpportunity]:
        """Get opportunities for specific exchange pair."""
        return [
            opp for opp in self.opportunities
            if opp.buy_exchange == buy_exchange and opp.sell_exchange == sell_exchange
        ]
    
    def save_scan_history(self, scan_id: str) -> None:
        """Save current scan results to history."""
        self.scan_history[scan_id] = self.opportunities.copy()
        logger.info(f"Saved scan {scan_id} with {len(self.opportunities)} opportunities")
    
    def get_scan_history(self, scan_id: str) -> List[ArbitrageOpportunity]:
        """Get historical scan results."""
        return self.scan_history.get(scan_id, [])
    
    async def close(self) -> None:
        """Close scanner and cleanup resources."""
        await self.manager.close_all()
        logger.info("Scanner closed")
