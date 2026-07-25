"""Application settings and configuration."""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Optional
from enum import Enum

CONFIG_DIR = Path.home() / ".arbitrage_scanner"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONFIG_DIR.mkdir(exist_ok=True)

class Theme(Enum):
    """Application theme."""
    DARK = "dark"
    LIGHT = "light"

@dataclass
class ExchangeSettings:
    """Exchange configuration."""
    enabled: bool = True
    api_key: Optional[str] = None
    api_secret: Optional[str] = None

class Settings:
    """Application settings manager."""
    
    def __init__(self):
        self.update_interval: int = 2  # seconds
        self.theme: Theme = Theme.DARK
        self.deposit_size: float = 100.0  # USDT
        self.min_spread: float = 0.5  # %
        self.min_profit: float = 10.0  # USDT
        self.min_liquidity: float = 100.0  # USDT
        self.min_volume: float = 100.0  # USDT
        self.sound_enabled: bool = True
        self.notifications_enabled: bool = True
        self.telegram_enabled: bool = False
        self.telegram_token: Optional[str] = None
        self.telegram_chat_id: Optional[str] = None
        self.discord_enabled: bool = False
        self.discord_webhook: Optional[str] = None
        self.exchanges: Dict[str, ExchangeSettings] = {
            "MEXC": ExchangeSettings(),
            "Bitget": ExchangeSettings(),
            "Gate.io": ExchangeSettings(),
            "KuCoin": ExchangeSettings(),
            "Bybit": ExchangeSettings(),
            "BingX": ExchangeSettings(),
        }
        self.manual_fees: Dict[str, Dict[str, float]] = {}
        
        self.load()
    
    def load(self) -> None:
        """Load settings from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if key == "theme":
                            self.theme = Theme(value)
                        elif key == "exchanges":
                            for ex_name, ex_data in value.items():
                                self.exchanges[ex_name] = ExchangeSettings(**ex_data)
                        else:
                            setattr(self, key, value)
            except Exception as e:
                print(f"Error loading config: {e}")
    
    def save(self) -> None:
        """Save settings to file."""
        try:
            data = {
                "update_interval": self.update_interval,
                "theme": self.theme.value,
                "deposit_size": self.deposit_size,
                "min_spread": self.min_spread,
                "min_profit": self.min_profit,
                "min_liquidity": self.min_liquidity,
                "min_volume": self.min_volume,
                "sound_enabled": self.sound_enabled,
                "notifications_enabled": self.notifications_enabled,
                "telegram_enabled": self.telegram_enabled,
                "telegram_token": self.telegram_token,
                "telegram_chat_id": self.telegram_chat_id,
                "discord_enabled": self.discord_enabled,
                "discord_webhook": self.discord_webhook,
                "exchanges": {k: asdict(v) for k, v in self.exchanges.items()},
                "manual_fees": self.manual_fees,
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

# Global settings instance
settings = Settings()
