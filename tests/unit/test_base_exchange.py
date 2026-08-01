"""Unit tests for BaseExchange and RateLimiter."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from app.api.base_exchange_v2 import BaseExchange, RateLimiter
from app.config.config_manager import ExchangeConfig
from app.models.exchange_data import Ticker, OrderBook, TradingFee


class MockExchange(BaseExchange):
    """Mock exchange for testing."""
    
    async def get_ticker(self, symbol: str):
        return await self._request("GET", f"/ticker?symbol={symbol}")
    
    async def get_order_book(self, symbol: str, limit: int = 20):
        return await self._request("GET", f"/orderbook?symbol={symbol}&limit={limit}")
    
    async def get_all_pairs(self):
        return await self._request("GET", "/pairs")
    
    async def get_trading_fee(self, symbol: str):
        return TradingFee(exchange="mock", symbol=symbol, maker=0.001, taker=0.001)
    
    async def _get_withdrawal_info_impl(self, coin: str):
        return {}
    
    async def _get_deposit_info_impl(self, coin: str):
        return {}


@pytest.fixture
def mock_config():
    """Create mock exchange configuration."""
    return ExchangeConfig(
        name="TestExchange",
        base_url="https://api.test.com",
        api_version="v1",
        timeout=10,
        rate_limit=10,
        rate_limit_period=1
    )


@pytest.fixture
async def mock_exchange(mock_config):
    """Create mock exchange instance."""
    exchange = MockExchange(mock_config)
    await exchange.initialize()
    yield exchange
    await exchange.close()


class TestRateLimiter:
    """Test RateLimiter functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_within_limit(self):
        """Test that rate limiter allows requests within limit."""
        limiter = RateLimiter(max_requests=5, period=1)
        
        # Should allow 5 requests without waiting
        for _ in range(5):
            await limiter.wait_if_needed()
        
        assert len(limiter.requests) == 5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_throttles_over_limit(self):
        """Test that rate limiter throttles when over limit."""
        limiter = RateLimiter(max_requests=2, period=1)
        
        start = datetime.now()
        
        # Make 3 requests
        for _ in range(3):
            await limiter.wait_if_needed()
        
        elapsed = (datetime.now() - start).total_seconds()
        
        # Should have waited approximately 1 second
        assert elapsed >= 0.9


class TestBaseExchange:
    """Test BaseExchange functionality."""
    
    @pytest.mark.asyncio
    async def test_exchange_initialization(self, mock_config):
        """Test exchange initialization."""
        exchange = MockExchange(mock_config)
        assert exchange.config == mock_config
        assert exchange.session is None
        
        await exchange.initialize()
        assert exchange.session is not None
        
        await exchange.close()
    
    @pytest.mark.asyncio
    async def test_exchange_api_request(self, mock_exchange):
        """Test making API requests."""
        with patch.object(mock_exchange.session, 'request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": "test"})
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_request.return_value = mock_response
            
            result = await mock_exchange._request("GET", "/test")
            
            assert result == {"data": "test"}
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exchange_handles_api_errors(self, mock_exchange):
        """Test exchange handles API errors."""
        with patch.object(mock_exchange.session, 'request') as mock_request:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.json = AsyncMock(return_value={"error": "Bad request"})
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            
            mock_request.return_value = mock_response
            
            with pytest.raises(Exception):
                await mock_exchange._request("GET", "/test")
    
    @pytest.mark.asyncio
    async def test_exchange_config_update(self, mock_exchange, mock_config):
        """Test dynamic config update."""
        original_timeout = mock_exchange.config.timeout
        
        mock_exchange.update_config(timeout=20)
        
        assert mock_exchange.config.timeout == 20
        assert mock_exchange.config.timeout != original_timeout
    
    @pytest.mark.asyncio
    async def test_exchange_requires_api_key_for_private_methods(self, mock_config):
        """Test that private methods require API key."""
        exchange = MockExchange(mock_config, api_key=None)
        
        result = await exchange.get_account_balance()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_exchange_with_api_credentials(self, mock_config):
        """Test exchange with API credentials."""
        exchange = MockExchange(
            mock_config,
            api_key="test_key",
            api_secret="test_secret"
        )
        
        assert exchange.api_key == "test_key"
        assert exchange.api_secret == "test_secret"


class TestExchangeMethods:
    """Test exchange interface methods."""
    
    @pytest.mark.asyncio
    async def test_get_ticker(self, mock_exchange):
        """Test get_ticker method."""
        with patch.object(mock_exchange, '_request') as mock_request:
            mock_request.return_value = {
                "symbol": "BTCUSD",
                "bid": 50000,
                "ask": 50001,
                "last": 50000.5
            }
            
            result = await mock_exchange.get_ticker("BTCUSD")
            
            mock_request.assert_called_once_with("GET", "/ticker?symbol=BTCUSD")
    
    @pytest.mark.asyncio
    async def test_get_order_book(self, mock_exchange):
        """Test get_order_book method."""
        with patch.object(mock_exchange, '_request') as mock_request:
            mock_request.return_value = {
                "bids": [[50000, 1.5], [49999, 2.0]],
                "asks": [[50001, 1.5], [50002, 2.0]]
            }
            
            result = await mock_exchange.get_order_book("BTCUSD", limit=20)
            
            mock_request.assert_called_once_with(
                "GET",
                "/orderbook?symbol=BTCUSD&limit=20"
            )
    
    @pytest.mark.asyncio
    async def test_get_trading_fee(self, mock_exchange):
        """Test get_trading_fee method."""
        fee = await mock_exchange.get_trading_fee("BTCUSD")
        
        assert fee is not None
        assert fee.exchange == "mock"
        assert fee.maker == 0.001
        assert fee.taker == 0.001
