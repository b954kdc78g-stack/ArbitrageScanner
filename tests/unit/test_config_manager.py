"""Unit tests for configuration manager."""

import pytest
import json
import tempfile
from pathlib import Path
from app.config.config_manager import ConfigurationManager, ExchangeConfig, NetworkType


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_config():
    """Sample exchange configuration."""
    return {
        "name": "TestExchange",
        "base_url": "https://api.test.com",
        "api_version": "v1",
        "timeout": 10,
        "rate_limit": 100,
        "rate_limit_period": 60,
        "supported_networks": ["ERC20", "TRC20"],
        "trading_fees": {"maker": 0.001, "taker": 0.001},
        "withdrawal_enabled": True,
        "deposit_enabled": True
    }


@pytest.mark.asyncio
async def test_configuration_manager_init(temp_config_dir):
    """Test ConfigurationManager initialization."""
    manager = ConfigurationManager(temp_config_dir)
    assert manager.config_path == Path(temp_config_dir)
    assert manager.exchange_configs == {}
    
    await manager.initialize()
    await manager.close()


@pytest.mark.asyncio
async def test_save_and_load_config(temp_config_dir, sample_config):
    """Test saving and loading configurations."""
    manager = ConfigurationManager(temp_config_dir)
    
    # Create config object
    config = ExchangeConfig(
        name=sample_config["name"],
        base_url=sample_config["base_url"],
        api_version=sample_config["api_version"],
        timeout=sample_config["timeout"],
        rate_limit=sample_config["rate_limit"],
        rate_limit_period=sample_config["rate_limit_period"]
    )
    
    # Save config
    assert manager.save_exchange_config("test_exchange", config)
    
    # Load config
    await manager.load_all_configs()
    loaded_config = manager.get_exchange_config("test_exchange")
    
    assert loaded_config is not None
    assert loaded_config.name == "TestExchange"
    assert loaded_config.base_url == "https://api.test.com"
    
    await manager.close()


def test_get_all_exchange_configs(temp_config_dir, sample_config):
    """Test getting all exchange configurations."""
    manager = ConfigurationManager(temp_config_dir)
    
    config1 = ExchangeConfig(
        name="Exchange1",
        base_url="https://api1.test.com",
        api_version="v1"
    )
    config2 = ExchangeConfig(
        name="Exchange2",
        base_url="https://api2.test.com",
        api_version="v1"
    )
    
    manager.save_exchange_config("exchange1", config1)
    manager.save_exchange_config("exchange2", config2)
    
    all_configs = manager.get_all_exchange_configs()
    assert len(all_configs) == 2
    assert "exchange1" in all_configs
    assert "exchange2" in all_configs


def test_parse_exchange_config(temp_config_dir, sample_config):
    """Test parsing exchange configuration."""
    manager = ConfigurationManager(temp_config_dir)
    
    parsed = manager._parse_exchange_config(sample_config)
    
    assert parsed.name == "TestExchange"
    assert parsed.base_url == "https://api.test.com"
    assert parsed.timeout == 10
    assert parsed.rate_limit == 100
    assert parsed.trading_fees["maker"] == 0.001


@pytest.mark.asyncio
async def test_fetch_remote_config(temp_config_dir):
    """Test fetching remote configuration."""
    manager = ConfigurationManager(temp_config_dir)
    await manager.initialize()
    
    # This would need a mock HTTP server in real tests
    # For now, just verify the method exists and handles errors
    result = await manager.fetch_remote_config("https://invalid.test.com/config.json")
    assert result is None  # Should fail gracefully
    
    await manager.close()
