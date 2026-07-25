"""Arbitrage opportunity model."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class ArbitrageOpportunity:
    """Represents an arbitrage opportunity."""
    coin: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    buy_liquidity: float
    sell_liquidity: float
    network: str
    buy_fee_percent: float
    sell_fee_percent: float
    withdrawal_fee: float
    deposit_fee: float
    network_fee: float
    gross_profit: float
    total_fees: float
    net_profit: float
    net_profit_percent: float
    min_deposit: float
    min_withdrawal: float
    min_buy_amount: float
    min_sell_amount: float
    deposit_available: bool
    withdrawal_available: bool
    update_time: datetime
    
    def is_viable(self, capital: float) -> bool:
        """Check if opportunity is viable for given capital."""
        return (
            capital >= self.min_deposit and
            capital >= self.min_withdrawal and
            capital >= self.min_buy_amount and
            capital >= self.min_sell_amount and
            self.deposit_available and
            self.withdrawal_available and
            self.net_profit > 0
        )
