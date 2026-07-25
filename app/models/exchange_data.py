"""Exchange data models."""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class OrderBook:
    """Order book data."""
    symbol: str
    bids: List[tuple]  # [(price, quantity), ...]
    asks: List[tuple]  # [(price, quantity), ...]
    timestamp: datetime

@dataclass
class Ticker:
    """Ticker data."""
    symbol: str
    last_price: float
    bid: float
    ask: float
    volume_24h: float
    timestamp: datetime

@dataclass
class WithdrawalInfo:
    """Withdrawal information."""
    coin: str
    network: str
    min_withdrawal: float
    withdrawal_fee: float
    is_available: bool

@dataclass
class DepositInfo:
    """Deposit information."""
    coin: str
    network: str
    min_deposit: float
    deposit_fee: float
    is_available: bool

@dataclass
class TradingFee:
    """Trading fee information."""
    symbol: str
    maker_fee: float
    taker_fee: float
    timestamp: datetime
