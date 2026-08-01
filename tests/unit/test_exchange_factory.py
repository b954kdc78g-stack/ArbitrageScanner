"""Unit tests for ExchangeFactory."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.api.exchange_factory import ExchangeFactory
from app.config.config_manager import ConfigurationManager, ExchangeConfig
from app.exchanges.binance import BinanceExchange
from app.exchanges.kraken import KrakenExchange
from app.exchanges.bybit import BybitExchange


@pytest.fixture
def mock_config_manager():
    """Create mock configuration manager."""
    manager = MagicMock(spec=ConfigurationManager)
    manager.get_exchange_config = MagicMock(return_value=ExchangeConfig(
        name="TestExchange",
        base_url="https://api.test.com",
        api_version="v1"
    ))
    manager.get_available_exchanges = MagicMock(return_value=["binance", "kraken", "bybit"])
    return manager


@pytest.fixture
def factory(mock_config_manager):
    """Create ExchangeFactory instance."""
    return ExchangeFactory(mock_config_manager)


class TestExchangeFactory:
    """Test ExchangeFactory functionality."""
    
    def test_factory_initialization(self, factory):
        """Test factory initialization."""
        assert factory.config_manager is not None
        assert factory.adapters == {}
        assert factory.exchange_instances == {}
    
    def test_register_adapter(self, factory):
        """Test registering exchange adapter."""
        factory.register_adapter("binance", BinanceExchange)
        
        assert "binance" in factory.adapters
        assert factory.adapters["binance"] == BinanceExchange
    
    def test_register_multiple_adapters(self, factory):
        """Test registering multiple adapters."""
        factory.register_adapter("binance", BinanceExchange)
        factory.register_adapter("kraken", KrakenExchange)
        factory.register_adapter("bybit", BybitExchange)
        
        assert len(factory.adapters) == 3
        assert all(name in factory.adapters for name in ["binance", "kraken", "bybit"])
    
    def test_get_registered_adapters(self, factory):
        """Test getting registered adapters."""
        factory.register_adapter("binance", BinanceExchange)
        factory.register_adapter("kraken", KrakenExchange)
        
        adapters = factory.get_registered_adapters()
        
        assert "binance" in adapters
        assert "kraken" in adapters
    
    @pytest.mark.asyncio
    async def test_create_exchange_success(self, factory):
        """Test creating exchange instance."""
        factory.register_adapter("binance", BinanceExchange)
        
        exchange = await factory.create_exchange("binance")
        
        assert exchange is not None
        assert isinstance(exchange, BinanceExchange)
    
    @pytest.mark.asyncio
    async def test_create_exchange_with_credentials(self, factory):
        """Test creating exchange with API credentials."""
        factory.register_adapter("binance", BinanceExchange)
        
        exchange = await factory.create_exchange(
            "binance",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        assert exchange is not None
        assert exchange.api_key == "test_key"
        assert exchange.api_secret == "test_secret"
    
    @pytest.mark.asyncio
    async def test_create_exchange_not_registered(self, factory):
        """Test creating unregistered exchange."""
        exchange = await factory.create_exchange("unknown_exchange")
        
        assert exchange is None
    
    @pytest.mark.asyncio
    async def test_close_exchange(self, factory):
        """Test closing exchange connection."""
        factory.register_adapter("binance", BinanceExchange)
        
        # Create and then close
        exchange = await factory.create_exchange("binance")
        result = await factory.close_exchange("binance")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_close_all_exchanges(self, factory):
        """Test closing all exchange connections."""
        factory.register_adapter("binance", BinanceExchange)
        factory.register_adapter("kraken", KrakenExchange)
        
        # Create exchanges
        await factory.create_exchange("binance")
        await factory.create_exchange("kraken")
        
        # Close all
        await factory.close_all()
        
        assert len(factory.exchange_instances) == 0
    
    def test_get_available_exchanges(self, factory, mock_config_manager):
        """Test getting available exchanges from config."""
        exchanges = factory.get_available_exchanges()
        
        assert len(exchanges) == 3
        assert all(name in exchanges for name in ["binance", "kraken", "bybit"])


class TestFactoryConfiguration:
    """Test factory configuration handling."""
    
    def test_factory_loads_config(self, mock_config_manager):
        """Test factory loads configuration."""
        factory = ExchangeFactory(mock_config_manager)
        
        config = factory.config_manager.get_exchange_config("binance")
        
        assert config is not None
        assert config.name == "TestExchange"
    
    @pytest.mark.asyncio
    async def test_factory_handles_config_errors(self, factory):
        """Test factory handles configuration errors gracefully."""
        factory.config_manager.get_exchange_config = MagicMock(return_value=None)
        
        exchange = await factory.create_exchange("binance")
        
        # Should handle error gracefully
        assert exchange is None
