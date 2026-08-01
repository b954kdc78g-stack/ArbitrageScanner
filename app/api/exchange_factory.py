"""Factory for creating exchange adapters."""

from typing import Dict, Optional, Type
from app.config.config_manager import ExchangeConfig, ConfigurationManager
from app.api.base_exchange_v2 import BaseExchange
from app.config.logger import setup_logger

logger = setup_logger(__name__)

class ExchangeFactory:
    """Factory for creating and managing exchange adapters."""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager
        self.adapters: Dict[str, Type[BaseExchange]] = {}
        self.instances: Dict[str, BaseExchange] = {}
    
    def register_adapter(self, exchange_name: str, adapter_class: Type[BaseExchange]) -> None:
        """
        Register an exchange adapter.
        
        Args:
            exchange_name: Name of the exchange (e.g., 'binance', 'kraken')
            adapter_class: Class that implements BaseExchange
        """
        if not issubclass(adapter_class, BaseExchange):
            raise ValueError(f"{adapter_class} must inherit from BaseExchange")
        
        self.adapters[exchange_name] = adapter_class
        logger.info(f"Registered adapter for {exchange_name}")
    
    async def create_exchange(
        self,
        exchange_name: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[BaseExchange]:
        """
        Create an exchange instance.
        
        Args:
            exchange_name: Name of the exchange
            api_key: API key (optional)
            api_secret: API secret (optional)
            use_cache: Use cached instance if available
        
        Returns:
            Exchange instance or None if creation failed
        """
        try:
            # Check cache
            if use_cache and exchange_name in self.instances:
                logger.debug(f"Using cached instance for {exchange_name}")
                return self.instances[exchange_name]
            
            # Check if adapter is registered
            if exchange_name not in self.adapters:
                logger.error(f"No adapter registered for {exchange_name}")
                return None
            
            # Get configuration
            config = self.config_manager.get_exchange_config(exchange_name)
            if not config:
                logger.error(f"No configuration found for {exchange_name}")
                return None
            
            # Create instance
            adapter_class = self.adapters[exchange_name]
            instance = adapter_class(config, api_key, api_secret)
            await instance.initialize()
            
            # Cache instance
            self.instances[exchange_name] = instance
            logger.info(f"Created exchange instance for {exchange_name}")
            
            return instance
        except Exception as e:
            logger.error(f"Error creating exchange {exchange_name}: {e}")
            return None
    
    async def get_exchange(self, exchange_name: str) -> Optional[BaseExchange]:
        """
        Get an exchange instance (from cache or create new).
        
        Args:
            exchange_name: Name of the exchange
        
        Returns:
            Exchange instance or None
        """
        if exchange_name in self.instances:
            return self.instances[exchange_name]
        
        return await self.create_exchange(exchange_name)
    
    def get_available_exchanges(self) -> list:
        """Get list of available exchanges."""
        return list(self.config_manager.get_all_exchange_configs().keys())
    
    def get_registered_adapters(self) -> list:
        """Get list of registered adapters."""
        return list(self.adapters.keys())
    
    async def close_all(self) -> None:
        """Close all exchange instances."""
        for exchange_name, instance in self.instances.items():
            try:
                await instance.close()
                logger.info(f"Closed {exchange_name}")
            except Exception as e:
                logger.error(f"Error closing {exchange_name}: {e}")
        
        self.instances.clear()
    
    async def close_exchange(self, exchange_name: str) -> bool:
        """Close a specific exchange instance."""
        if exchange_name in self.instances:
            try:
                await self.instances[exchange_name].close()
                del self.instances[exchange_name]
                logger.info(f"Closed {exchange_name}")
                return True
            except Exception as e:
                logger.error(f"Error closing {exchange_name}: {e}")
                return False
        return False
