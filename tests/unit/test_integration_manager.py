"""Unit tests for IntegrationManager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.integration_manager import IntegrationManager
from app.models.exchange_data import Ticker, ArbitrageOpportunity


@pytest.fixture
async def integration_manager():
    """Create IntegrationManager instance."""
    manager = IntegrationManager("config/exchanges")
    yield manager
    await manager.shutdown()


class TestIntegrationManagerInitialization:
    """Test IntegrationManager initialization."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test manager initialization."""
        manager = IntegrationManager("config/exchanges")
        
        assert manager.config_manager is not None
        assert manager.factory is not None
        assert manager.active_exchanges == {}
        assert manager.is_running is False
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_manager_initialize_async(self, integration_manager):
        """Test async initialization."""
        result = await integration_manager.initialize()
        
        assert result is True
        # Adapters should be registered
        adapters = integration_manager.factory.get_registered_adapters()
        assert "binance" in adapters
        assert "kraken" in adapters
        assert "bybit" in adapters


class TestExchangeActivation:
    """Test exchange activation/deactivation."""
    
    @pytest.mark.asyncio
    async def test_activate_exchange(self, integration_manager):
        """Test activating a single exchange."""
        await integration_manager.initialize()
        
        result = await integration_manager.activate_exchange("binance")
        
        assert result is True
        assert "binance" in integration_manager.active_exchanges
    
    @pytest.mark.asyncio
    async def test_activate_exchange_with_credentials(self, integration_manager):
        """Test activating exchange with API credentials."""
        await integration_manager.initialize()
        
        result = await integration_manager.activate_exchange(
            "binance",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        assert result is True
        exchange = integration_manager.active_exchanges.get("binance")
        assert exchange.api_key == "test_key"
    
    @pytest.mark.asyncio
    async def test_activate_unknown_exchange(self, integration_manager):
        """Test activating unknown exchange."""
        await integration_manager.initialize()
        
        result = await integration_manager.activate_exchange("unknown")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_deactivate_exchange(self, integration_manager):
        """Test deactivating exchange."""
        await integration_manager.initialize()
        await integration_manager.activate_exchange("binance")
        
        result = await integration_manager.deactivate_exchange("binance")
        
        assert result is True
        assert "binance" not in integration_manager.active_exchanges
    
    @pytest.mark.asyncio
    async def test_deactivate_inactive_exchange(self, integration_manager):
        """Test deactivating non-active exchange."""
        await integration_manager.initialize()
        
        result = await integration_manager.deactivate_exchange("binance")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_activate_all_exchanges(self, integration_manager):
        """Test activating all exchanges."""
        await integration_manager.initialize()
        
        results = await integration_manager.activate_all_exchanges()
        
        assert len(results) > 0
        assert any(results.values())  # At least one should succeed


class TestTickerFetching:
    """Test ticker fetching functionality."""
    
    @pytest.mark.asyncio
    async def test_get_ticker_from_exchange(self, integration_manager):
        """Test getting ticker from specific exchange."""
        await integration_manager.initialize()
        await integration_manager.activate_exchange("binance")
        
        with patch.object(
            integration_manager.active_exchanges["binance"],
            "get_ticker"
        ) as mock_ticker:
            mock_ticker.return_value = Ticker(
                exchange="binance",
                symbol="BTCUSD",
                bid=50000,
                ask=50001,
                last=50000.5,
                volume_24h=1000,
                timestamp=None
            )
            
            ticker = await integration_manager.get_ticker("binance", "BTCUSD")
            
            assert ticker is not None
            assert ticker.exchange == "binance"
            assert ticker.bid == 50000
    
    @pytest.mark.asyncio
    async def test_get_ticker_inactive_exchange(self, integration_manager):
        """Test getting ticker from inactive exchange."""
        await integration_manager.initialize()
        
        ticker = await integration_manager.get_ticker("binance", "BTCUSD")
        
        assert ticker is None
    
    @pytest.mark.asyncio
    async def test_get_tickers_from_all_exchanges(self, integration_manager):
        """Test getting tickers from all active exchanges."""
        await integration_manager.initialize()
        await integration_manager.activate_exchange("binance")
        await integration_manager.activate_exchange("kraken")
        
        with patch.object(
            integration_manager.active_exchanges["binance"],
            "get_ticker"
        ) as mock_binance:
            with patch.object(
                integration_manager.active_exchanges["kraken"],
                "get_ticker"
            ) as mock_kraken:
                mock_binance.return_value = Ticker(
                    exchange="binance",
                    symbol="BTCUSD",
                    bid=50000,
                    ask=50001,
                    last=50000.5,
                    volume_24h=1000,
                    timestamp=None
                )
                mock_kraken.return_value = Ticker(
                    exchange="kraken",
                    symbol="BTCUSD",
                    bid=50002,
                    ask=50003,
                    last=50002.5,
                    volume_24h=800,
                    timestamp=None
                )
                
                tickers = await integration_manager.get_tickers("BTCUSD")
                
                assert len(tickers) == 2
                assert "binance" in tickers
                assert "kraken" in tickers


class TestArbitrageDetection:
    """Test arbitrage opportunity detection."""
    
    @pytest.mark.asyncio
    async def test_find_arbitrage_opportunities(self, integration_manager):
        """Test finding arbitrage opportunities."""
        await integration_manager.initialize()
        await integration_manager.activate_exchange("binance")
        await integration_manager.activate_exchange("kraken")
        
        with patch.object(
            integration_manager,
            "get_tickers"
        ) as mock_tickers:
            # Binance: bid=50000, ask=50001
            # Kraken: bid=50010, ask=50011
            # Spread = (50010 - 50001) / 50001 * 100 = 0.018% (not profitable)
            
            mock_tickers.return_value = {
                "binance": Ticker(
                    exchange="binance",
                    symbol="BTCUSD",
                    bid=50000,
                    ask=50001,
                    last=50000.5,
                    volume_24h=1000,
                    timestamp=None
                ),
                "kraken": Ticker(
                    exchange="kraken",
                    symbol="BTCUSD",
                    bid=50100,  # Large spread for profit
                    ask=50101,
                    last=50100.5,
                    volume_24h=800,
                    timestamp=None
                )
            }
            
            opportunities = await integration_manager.find_arbitrage_opportunities(
                ["BTCUSD"],
                min_spread_percent=0.1
            )
            
            assert len(opportunities) > 0
            assert opportunities[0].symbol == "BTCUSD"
            assert opportunities[0].buy_exchange == "binance"
            assert opportunities[0].sell_exchange == "kraken"
    
    @pytest.mark.asyncio
    async def test_no_opportunities_below_threshold(self, integration_manager):
        """Test no opportunities when spread below threshold."""
        await integration_manager.initialize()
        await integration_manager.activate_exchange("binance")
        await integration_manager.activate_exchange("kraken")
        
        with patch.object(
            integration_manager,
            "get_tickers"
        ) as mock_tickers:
            mock_tickers.return_value = {
                "binance": Ticker(
                    exchange="binance",
                    symbol="BTCUSD",
                    bid=50000,
                    ask=50001,
                    last=50000.5,
                    volume_24h=1000,
                    timestamp=None
                ),
                "kraken": Ticker(
                    exchange="kraken",
                    symbol="BTCUSD",
                    bid=50001,
                    ask=50002,
                    last=50001.5,
                    volume_24h=800,
                    timestamp=None
                )
            }
            
            opportunities = await integration_manager.find_arbitrage_opportunities(
                ["BTCUSD"],
                min_spread_percent=10.0  # High threshold
            )
            
            assert len(opportunities) == 0


class TestPairFetching:
    """Test trading pair fetching."""
    
    @pytest.mark.asyncio
    async def test_get_all_pairs(self, integration_manager):
        """Test getting all pairs from exchanges."""
        await integration_manager.initialize()
        await integration_manager.activate_exchange("binance")
        
        with patch.object(
            integration_manager.active_exchanges["binance"],
            "get_all_pairs"
        ) as mock_pairs:
            mock_pairs.return_value = ["BTCUSD", "ETHUSD", "ADAUSD"]
            
            pairs = await integration_manager.get_all_pairs()
            
            assert "binance" in pairs
            assert "BTCUSD" in pairs["binance"]
    
    @pytest.mark.asyncio
    async def test_get_common_pairs(self, integration_manager):
        """Test getting common pairs across exchanges."""
        await integration_manager.initialize()
        
        # Common pairs should be empty without data
        common = integration_manager.get_common_pairs()
        
        assert common == []


class TestManagerShutdown:
    """Test manager shutdown."""
    
    @pytest.mark.asyncio
    async def test_manager_shutdown(self, integration_manager):
        """Test manager shutdown."""
        await integration_manager.initialize()
        await integration_manager.activate_exchange("binance")
        
        await integration_manager.shutdown()
        
        assert len(integration_manager.active_exchanges) == 0
