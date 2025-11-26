
from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics

class StatisticsCalculator:
    
    def calculate_interarrival_std(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Optional[float]:
        if len(transactions) < 2:
            return None
        
        timestamps = []
        for tx in transactions:
            ts = self._get_timestamp_int(tx)
            if ts:
                timestamps.append(ts)
        
        if len(timestamps) < 2:
            return None
        
        timestamps.sort()
        
        intervals = []
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            if interval > 0:
                intervals.append(interval)
        
        if len(intervals) < 2:
            return None
        
        try:
            return statistics.stdev(intervals)
        except statistics.StatisticsError:
            return None
    
    def calculate_interarrival_mean(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Optional[float]:
        if len(transactions) < 2:
            return None
        
        timestamps = []
        for tx in transactions:
            ts = self._get_timestamp_int(tx)
            if ts:
                timestamps.append(ts)
        
        if len(timestamps) < 2:
            return None
        
        timestamps.sort()
        
        intervals = []
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            if interval > 0:
                intervals.append(interval)
        
        if not intervals:
            return None
        
        try:
            return statistics.mean(intervals)
        except statistics.StatisticsError:
            return None
    
    def _get_timestamp_int(self, tx: Dict[str, Any]) -> Optional[int]:
        timestamp = tx.get("timestamp", 0)
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except:
                return None
        return int(timestamp) if timestamp else None
    
    def check_prerequisites(
        self,
        transactions: List[Dict[str, Any]],
        min_edges: int = 10
    ) -> bool:
        return len(transactions) >= min_edges

