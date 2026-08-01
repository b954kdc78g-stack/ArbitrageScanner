"""Configuration manager for exchanges."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import aiohttp
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class NetworkType(Enum):
    """Network types for withdrawals/deposits."""
    ERC20 = "ERC20"
    TRC20 = "TRC20"
    BEP20 = "BEP20"
    POLYGON = "POLYGON"
    ARBITRUM = "ARBITRUM"
    OPTIMISM = "OPTIMISM"

@dataclass
class ExchangeConfig:
    """Exchange configuration."""
    name: str
    base_url: str
    api_version: str
    timeout: int = 10
    rate_limit: int = 100
    rate_limit_period: int = 60
    supported_networks: List[str] = field(default_factory=list)
    trading_fees: Dict[str, float] = field(default_factory=lambda: {"maker": 0.001, "taker": 0.001})
    withdrawal_enabled: bool = True
    deposit_enabled: bool = True
    extra_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CoinConfig:
    """Coin/Token configuration."""
    symbol: str
    name: str
    networks: Dict[str, Dict[str, Any]] = field(default_factory=dict)

class ConfigurationManager:
    """Manager for loading and managing exchange configurations."""
    
    def __init__(self, config_path: str = "config/exchanges"):
        self.config_path = Path(config_path)
        self.config_path.mkdir(parents=True, exist_ok=True)
        self.exchange_configs: Dict[str, ExchangeConfig] = {}
        self.coin_configs: Dict[str, CoinConfig] = {}
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize configuration manager."""
        self.session = aiohttp.ClientSession()
        await self.load_all_configs()
    
    async def load_all_configs(self) -> None:
        """Load all exchange configurations."""
        config_files = list(self.config_path.glob("*.json"))
        
        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    exchange_name = config_file.stem
                    config = self._parse_exchange_config(data)
                    self.exchange_configs[exchange_name] = config
                    logger.info(f"Loaded config for {exchange_name}")
            except Exception as e:
                logger.error(f"Error loading config from {config_file}: {e}")
    
    def _parse_exchange_config(self, data: Dict[str, Any]) -> ExchangeConfig:
        """Parse exchange configuration from dictionary."""
        return ExchangeConfig(
            name=data.get("name", "Unknown"),
            base_url=data.get("base_url", ""),
            api_version=data.get("api_version", "v1"),
            timeout=data.get("timeout", 10),
            rate_limit=data.get("rate_limit", 100),
            rate_limit_period=data.get("rate_limit_period", 60),
            supported_networks=data.get("supported_networks", []),
            trading_fees=data.get("trading_fees", {"maker": 0.001, "taker": 0.001}),
            withdrawal_enabled=data.get("withdrawal_enabled", True),
            deposit_enabled=data.get("deposit_enabled", True),
            extra_params=data.get("extra_params", {})
        )
    
    def get_exchange_config(self, exchange_name: str) -> Optional[ExchangeConfig]:
        """Get exchange configuration."""
        return self.exchange_configs.get(exchange_name)
    
    def get_all_exchange_configs(self) -> Dict[str, ExchangeConfig]:
        """Get all exchange configurations."""
        return self.exchange_configs
    
    def save_exchange_config(self, exchange_name: str, config: ExchangeConfig) -> bool:
        """Save exchange configuration to file."""
        try:
            config_file = self.config_path / f"{exchange_name}.json"
            
            data = {
                "name": config.name,
                "base_url": config.base_url,
                "api_version": config.api_version,
                "timeout": config.timeout,
                "rate_limit": config.rate_limit,
                "rate_limit_period": config.rate_limit_period,
                "supported_networks": config.supported_networks,
                "trading_fees": config.trading_fees,
                "withdrawal_enabled": config.withdrawal_enabled,
                "deposit_enabled": config.deposit_enabled,
                "extra_params": config.extra_params
            }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.exchange_configs[exchange_name] = config
            logger.info(f"Saved config for {exchange_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    async def fetch_remote_config(self, remote_url: str) -> Optional[Dict[str, Any]]:
        """Fetch configuration from remote URL."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(remote_url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch remote config: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching remote config: {e}")
            return None
    
    async def close(self) -> None:
        """Close configuration manager."""
        if self.session:
            await self.session.close()
