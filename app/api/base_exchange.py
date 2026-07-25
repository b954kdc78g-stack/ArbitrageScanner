"""Base exchange API client."""

import aiohttp
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from app.models.exchange_data import OrderBook, Ticker, WithdrawalInfo, DepositInfo, TradingFee
from app.config.logger import setup_logger
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

logger = setup_logger(__name__)

class BaseExchange(ABC):
    """Base class for exchange API clients."""
    
    def __init__(self, name: str, base_url: str, timeout: int = 10):
        self.name = name
        self.base_url = base_url
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.available_networks: Dict[str, set] = {}  # coin -> set of networks
        self.trading_fees: Dict[str, Tuple[float, float]] = {}  # symbol -> (maker, taker)
    
    async def init(self) -> None:
        """Initialize session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close(self) -> None:
        """Close session."""
        if self.session:
            await self.session.close()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request with retry."""
        await self.init()
        url = f"{self.base_url}{endpoint}"
        try:
            async with self.session.get(url, params=params, timeout=self.timeout) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"{self.name}: HTTP {resp.status} for {endpoint}")
                    return {}
        except asyncio.TimeoutError:
            logger.error(f"{self.name}: Timeout on {endpoint}")
            raise
        except Exception as e:
            logger.error(f"{self.name}: Error fetching {endpoint}: {e}")
            raise
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker data."""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book."""
        pass
    
    @abstractmethod
    async def get_all_pairs(self) -> List[str]:
        """Get all trading pairs."""
        pass
    
    @abstractmethod
    async def get_withdrawal_info(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal information by network."""
        pass
    
    @abstractmethod
    async def get_deposit_info(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit information by network."""
        pass
    
    @abstractmethod
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fees."""
        pass
