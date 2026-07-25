"""History and storage service for arbitrage data."""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json
from pathlib import Path
from app.models.exchange_data import ArbitrageOpportunity
from app.services.profit_calculator import ProfitCalculation
from app.config.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class ScanRecord:
    """Record of a single arbitrage scan."""
    scan_id: str
    timestamp: datetime
    opportunities_count: int
    best_opportunity: Optional[Dict]
    duration_seconds: float

class HistoryService:
    """Service for managing arbitrage history and storage."""
    
    def __init__(self, storage_path: str = "data/history"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.scan_records: List[ScanRecord] = []
        self.opportunities_cache: Dict[str, List[ArbitrageOpportunity]] = {}
        self.profit_calculations_cache: Dict[str, ProfitCalculation] = {}
    
    def save_scan_results(
        self,
        scan_id: str,
        opportunities: List[ArbitrageOpportunity],
        duration_seconds: float
    ) -> bool:
        """
        Save scan results to file and cache.
        
        Args:
            scan_id: Unique scan identifier
            opportunities: List of found opportunities
            duration_seconds: Scan duration
        
        Returns:
            True if saved successfully
        """
        try:
            # Create record
            best_opp = None
            if opportunities:
                best_opp = {
                    "symbol": opportunities[0].symbol,
                    "profit_percent": opportunities[0].profit_percent,
                    "buy_exchange": opportunities[0].buy_exchange,
                    "sell_exchange": opportunities[0].sell_exchange
                }
            
            record = ScanRecord(
                scan_id=scan_id,
                timestamp=datetime.now(),
                opportunities_count=len(opportunities),
                best_opportunity=best_opp,
                duration_seconds=duration_seconds
            )
            
            self.scan_records.append(record)
            self.opportunities_cache[scan_id] = opportunities
            
            # Save to file
            file_path = self.storage_path / f"scan_{scan_id}.json"
            data = {
                "scan_id": scan_id,
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration_seconds,
                "opportunities_count": len(opportunities),
                "opportunities": [self._opportunity_to_dict(opp) for opp in opportunities]
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved scan {scan_id} with {len(opportunities)} opportunities")
            return True
        except Exception as e:
            logger.error(f"Error saving scan results: {e}")
            return False
    
    def save_profit_calculation(
        self,
        calc_id: str,
        calculation: ProfitCalculation,
        opportunity: ArbitrageOpportunity
    ) -> bool:
        """Save profit calculation result."""
        try:
            self.profit_calculations_cache[calc_id] = calculation
            
            file_path = self.storage_path / f"calc_{calc_id}.json"
            data = {
                "calc_id": calc_id,
                "timestamp": calculation.timestamp.isoformat(),
                "opportunity": self._opportunity_to_dict(opportunity),
                "net_profit": calculation.net_profit,
                "profit_percent": calculation.profit_percent,
                "maker_fee_buy": calculation.maker_fee_buy,
                "taker_fee_sell": calculation.taker_fee_sell,
                "withdrawal_fee": calculation.withdrawal_fee,
                "deposit_fee": calculation.deposit_fee
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved profit calculation {calc_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving profit calculation: {e}")
            return False
    
    def get_scan_results(self, scan_id: str) -> Optional[List[ArbitrageOpportunity]]:
        """Get scan results by ID."""
        return self.opportunities_cache.get(scan_id)
    
    def get_profit_calculation(self, calc_id: str) -> Optional[ProfitCalculation]:
        """Get profit calculation by ID."""
        return self.profit_calculations_cache.get(calc_id)
    
    def get_recent_scans(self, limit: int = 10) -> List[ScanRecord]:
        """Get recent scan records."""
        return sorted(
            self.scan_records,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]
    
    def get_scans_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[ScanRecord]:
        """Get scans within date range."""
        return [
            record for record in self.scan_records
            if start_date <= record.timestamp <= end_date
        ]
    
    def get_statistics(self) -> Dict:
        """Get statistics from all scans."""
        if not self.scan_records:
            return {
                "total_scans": 0,
                "total_opportunities": 0,
                "avg_opportunities_per_scan": 0,
                "avg_scan_duration": 0
            }
        
        total_opps = sum(r.opportunities_count for r in self.scan_records)
        avg_duration = sum(r.duration_seconds for r in self.scan_records) / len(self.scan_records)
        
        return {
            "total_scans": len(self.scan_records),
            "total_opportunities": total_opps,
            "avg_opportunities_per_scan": total_opps / len(self.scan_records),
            "avg_scan_duration": avg_duration,
            "last_scan": self.scan_records[-1].timestamp.isoformat() if self.scan_records else None
        }
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """Clean up old records."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            old_records = [r for r in self.scan_records if r.timestamp < cutoff_date]
            
            for record in old_records:
                file_path = self.storage_path / f"scan_{record.scan_id}.json"
                if file_path.exists():
                    file_path.unlink()
                
                if record.scan_id in self.opportunities_cache:
                    del self.opportunities_cache[record.scan_id]
            
            self.scan_records = [r for r in self.scan_records if r not in old_records]
            
            logger.info(f"Cleaned up {len(old_records)} old records")
            return len(old_records)
        except Exception as e:
            logger.error(f"Error cleaning up records: {e}")
            return 0
    
    def export_data(self, export_path: str) -> bool:
        """Export all data to file."""
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "exported_at": datetime.now().isoformat(),
                "statistics": self.get_statistics(),
                "recent_scans": [asdict(r) for r in self.get_recent_scans(100)],
                "opportunities_count": len(self.opportunities_cache),
                "calculations_count": len(self.profit_calculations_cache)
            }
            
            with open(export_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Exported data to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False
    
    @staticmethod
    def _opportunity_to_dict(opp: ArbitrageOpportunity) -> Dict:
        """Convert opportunity to dictionary."""
        return {
            "symbol": opp.symbol,
            "buy_exchange": opp.buy_exchange,
            "sell_exchange": opp.sell_exchange,
            "buy_price": float(opp.buy_price),
            "sell_price": float(opp.sell_price),
            "profit_percent": float(opp.profit_percent),
            "timestamp": opp.timestamp.isoformat()
        }
