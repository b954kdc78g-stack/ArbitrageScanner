"""Profit calculator service."""

from typing import Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from app.models.exchange_data import TradingFee, WithdrawalInfo, DepositInfo
from app.config.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class ProfitCalculation:
    """Profit calculation result."""
    gross_profit: float
    withdrawal_fee: float
    deposit_fee: float
    maker_fee_buy: float
    taker_fee_sell: float
    net_profit: float
    profit_percent: float
    timestamp: datetime

class ProfitCalculator:
    """Service for calculating arbitrage profits."""
    
    def __init__(self):
        self.calculation_history: Dict[str, ProfitCalculation] = {}
    
    async def calculate_arbitrage_profit(
        self,
        symbol: str,
        buy_amount: float,
        buy_price: float,
        sell_price: float,
        buy_exchange: str,
        sell_exchange: str,
        buy_trading_fee: Optional[TradingFee] = None,
        sell_trading_fee: Optional[TradingFee] = None,
        withdrawal_info: Optional[Dict[str, WithdrawalInfo]] = None,
        deposit_info: Optional[Dict[str, DepositInfo]] = None,
        network: str = "USDT"
    ) -> ProfitCalculation:
        """
        Calculate net profit considering all fees.
        
        Args:
            symbol: Trading pair symbol
            buy_amount: Amount to buy (in base currency)
            buy_price: Purchase price
            sell_price: Sale price
            buy_exchange: Exchange where buying
            sell_exchange: Exchange where selling
            buy_trading_fee: Trading fee for buying
            sell_trading_fee: Trading fee for selling
            withdrawal_info: Withdrawal information from buy exchange
            deposit_info: Deposit information to sell exchange
            network: Network to use for transfer
        
        Returns:
            ProfitCalculation with all fee details
        """
        try:
            # Initial purchase cost
            cost = buy_amount * buy_price
            
            # Maker fee on buy (usually cheaper)
            maker_fee_buy = cost * (buy_trading_fee.maker_fee if buy_trading_fee else 0.001)
            total_cost = cost + maker_fee_buy
            
            # Withdrawal fee (converting from quote to base currency if needed)
            withdrawal_fee = 0.0
            if withdrawal_info and network in withdrawal_info:
                withdrawal_fee = withdrawal_info[network].withdrawal_fee
            
            # Amount received after withdrawal
            amount_after_withdrawal = buy_amount - withdrawal_fee
            
            # Deposit fee (usually on receiving side)
            deposit_fee = 0.0
            if deposit_info and network in deposit_info:
                deposit_fee = deposit_info[network].deposit_fee
            
            # Final amount available for selling
            final_amount = amount_after_withdrawal - deposit_fee
            
            # Revenue from selling (taker fee usually higher)
            revenue = final_amount * sell_price
            taker_fee_sell = revenue * (sell_trading_fee.taker_fee if sell_trading_fee else 0.001)
            net_revenue = revenue - taker_fee_sell
            
            # Profit calculation
            gross_profit = net_revenue - cost
            total_fees = maker_fee_buy + withdrawal_fee + deposit_fee + taker_fee_sell
            net_profit = gross_profit - total_fees
            
            profit_percent = (net_profit / total_cost) * 100 if total_cost > 0 else 0
            
            calculation = ProfitCalculation(
                gross_profit=gross_profit,
                withdrawal_fee=withdrawal_fee,
                deposit_fee=deposit_fee,
                maker_fee_buy=maker_fee_buy,
                taker_fee_sell=taker_fee_sell,
                net_profit=net_profit,
                profit_percent=profit_percent,
                timestamp=datetime.now()
            )
            
            logger.info(
                f"Profit calculation: {buy_exchange}->{sell_exchange} {symbol} "
                f"Net: {net_profit:.6f} ({profit_percent:.2f}%)"
            )
            
            return calculation
        except Exception as e:
            logger.error(f"Error calculating profit: {e}")
            raise
    
    def calculate_break_even_price(
        self,
        buy_price: float,
        total_fees_percent: float = 0.5
    ) -> float:
        """
        Calculate break-even sell price considering fees.
        
        Args:
            buy_price: Purchase price
            total_fees_percent: Total fees as percentage (0-100)
        
        Returns:
            Minimum sell price to break even
        """
        fee_multiplier = 1 + (total_fees_percent / 100)
        return buy_price * fee_multiplier
    
    def calculate_minimum_arbitrage(
        self,
        buy_price: float,
        sell_price: float,
        buy_fee_percent: float = 0.1,
        sell_fee_percent: float = 0.1,
        network_fee_percent: float = 0.05
    ) -> Tuple[float, bool]:
        """
        Calculate minimum arbitrage profit percentage.
        
        Args:
            buy_price: Purchase price
            sell_price: Sale price
            buy_fee_percent: Buying fee percentage
            sell_fee_percent: Selling fee percentage
            network_fee_percent: Network transfer fee percentage
        
        Returns:
            Tuple of (profit_percent, is_profitable)
        """
        total_fee_percent = buy_fee_percent + sell_fee_percent + network_fee_percent
        price_diff_percent = ((sell_price - buy_price) / buy_price) * 100
        net_profit_percent = price_diff_percent - total_fee_percent
        
        return net_profit_percent, net_profit_percent > 0
    
    def save_calculation(self, calculation_id: str, calculation: ProfitCalculation) -> None:
        """Save calculation to history."""
        self.calculation_history[calculation_id] = calculation
        logger.info(f"Saved calculation {calculation_id}")
    
    def get_calculation_history(self, calculation_id: str) -> Optional[ProfitCalculation]:
        """Get historical calculation."""
        return self.calculation_history.get(calculation_id)
    
    def get_all_calculations(self) -> Dict[str, ProfitCalculation]:
        """Get all calculations."""
        return self.calculation_history
