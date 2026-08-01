"""Improved base exchange interface with dynamic configuration."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import aiohttp
import asyncio
from datetime import datetime, timedelta
from app.config.config_manager import ExchangeConfig
from app.models.exchange_data import (
    Ticker, OrderBook, TradingFee, WithdrawalInfo, 
    DepositInfo, ArbitrageOpportunity
)
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class RateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, max_requests: int, period: int):
        self.max_requests = max_requests
        self.period = period
        self.requests: List[datetime] = []
    
    async def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.period)
        
        # Remove old requests outside the period
        self.requests = [req for req in self.requests if req > cutoff]
        
        if len(self.requests) >= self.max_requests:
            wait_time = (self.requests[0] - cutoff).total_seconds()
            if wait_time > 0:
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self.requests = []
        
        self.requests.append(now)

class BaseExchange(ABC):
    """
    Abstract base class for exchange adapters.
    All exchanges must implement these methods.
    Configuration is injected and dynamic.
    """
    
    def __init__(self, config: ExchangeConfig, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.config = config
        self.api_key = api_key
        self.api_secret = api_secret
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = RateLimiter(config.rate_limit, config.rate_limit_period)
    
    async def initialize(self) -> None:
        """Initialize exchange client."""
        if not self.session:
            connector = aiohttp.TCPConnector(limit=10)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
        logger.info(f"Initialized {self.config.name}")
    
    async def close(self) -> None:
        """Close exchange client."""
        if self.session:
            await self.session.close()
        logger.info(f"Closed {self.config.name}")
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for aiohttp
        
        Returns:
            Response JSON
        """
        if not self.session:
            await self.initialize()
        
        await self.rate_limiter.wait_if_needed()
        
        url = f"{self.config.base_url}/{self.config.api_version}{endpoint}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                data = await response.json()
                
                if response.status >= 400:
                    logger.error(f"API error from {self.config.name}: {response.status} {data}")
                    raise Exception(f"API error: {response.status}")
                
                return data
        except asyncio.TimeoutError:
            logger.error(f"Timeout requesting {self.config.name}: {endpoint}")
            raise
        except Exception as e:
            logger.error(f"Error requesting {self.config.name}: {e}")
            raise
    
    # Abstract methods that all exchanges must implement
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker information for a symbol."""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Get order book for a symbol."""
        pass
    
    @abstractmethod
    async def get_all_pairs(self) -> List[str]:
        """Get all available trading pairs."""
        pass
    
    @abstractmethod
    async def get_trading_fee(self, symbol: str) -> Optional[TradingFee]:
        """Get trading fee for a symbol."""
        pass
    
    async def get_withdrawal_info(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Get withdrawal information by network."""
        if not self.config.withdrawal_enabled:
            return {}
        return await self._get_withdrawal_info_impl(coin)
    
    @abstractmethod
    async def _get_withdrawal_info_impl(self, coin: str) -> Dict[str, WithdrawalInfo]:
        """Implementation of withdrawal info fetching."""
        pass
    
    async def get_deposit_info(self, coin: str) -> Dict[str, DepositInfo]:
        """Get deposit information by network."""
        if not self.config.deposit_enabled:
            return {}
        return await self._get_deposit_info_impl(coin)
    
    @abstractmethod
    async def _get_deposit_info_impl(self, coin: str) -> Dict[str, DepositInfo]:
        """Implementation of deposit info fetching."""
        pass
    
    # Optional methods for trading
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        order_type: str = "limit"
    ) -> Optional[Dict[str, Any]]:
        """Place an order (requires API key)."""
        if not self.api_key:
            logger.error(f"API key required for {self.config.name}")
            return None
        return await self._place_order_impl(symbol, side, quantity, price, order_type)
    
    async def _place_order_impl(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        order_type: str = "limit"
    ) -> Optional[Dict[str, Any]]:
        """Implementation of order placement."""
        raise NotImplementedError(f"{self.config.name} does not support trading")
    
    async def get_account_balance(self) -> Optional[Dict[str, float]]:
        """Get account balances (requires API key)."""
        if not self.api_key:
            logger.error(f"API key required for {self.config.name}")
            return None
        return await self._get_account_balance_impl()
    
    async def _get_account_balance_impl(self) -> Optional[Dict[str, float]]:
        """Implementation of account balance fetching."""
        raise NotImplementedError(f"{self.config.name} does not support balance queries")
    
    async def withdraw(
        self,
        coin: str,
        amount: float,
        address: str,
        network: str,
        tag: Optional[str] = None
    ) -> Optional[str]:
        """Withdraw coins (requires API key)."""
        if not self.api_key:
            logger.error(f"API key required for {self.config.name}")
            return None
        if not self.config.withdrawal_enabled:
            logger.error(f"Withdrawals not enabled for {self.config.name}")
            return None
        return await self._withdraw_impl(coin, amount, address, network, tag)
    
    async def _withdraw_impl(
        self,
        coin: str,
        amount: float,
        address: str,
        network: str,
        tag: Optional[str] = None
    ) -> Optional[str]:
        """Implementation of withdrawal."""
        raise NotImplementedError(f"{self.config.name} does not support withdrawals")
    
    def get_config(self) -> ExchangeConfig:
        """Get exchange configuration."""
        return self.config
    
    def update_config(self, **kwargs) -> None:
        """Update exchange configuration dynamically."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated {self.config.name} config: {key}={value}")
