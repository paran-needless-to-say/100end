from __future__ import annotations

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

class TransactionHistory:
    
    def __init__(self, max_history_days: int = 365):
        self.max_history_days = max_history_days
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def add_transaction(self, address: str, tx_data: Dict[str, Any]) -> None:
        self._history[address].append(tx_data)
        self._cleanup_old_transactions(address)
    
    def get_window_transactions(
        self,
        address: str,
        current_timestamp: int,
        duration_sec: int
    ) -> List[Dict[str, Any]]:
        txs = self._history.get(address, [])
        window_start = current_timestamp - duration_sec
        
        def get_timestamp_int(tx: Dict[str, Any]) -> int:
            timestamp = tx.get("timestamp", 0)
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    return int(dt.timestamp())
                except:
                    return 0
            return int(timestamp) if timestamp else 0
        
        return [
            tx for tx in txs
            if window_start <= get_timestamp_int(tx) <= current_timestamp
        ]
    
    def _cleanup_old_transactions(self, address: str) -> None:
        max_timestamp = int(datetime.now().timestamp()) - (self.max_history_days * 86400)
        
        def get_timestamp_int(tx: Dict[str, Any]) -> int:
            timestamp = tx.get("timestamp", 0)
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    return int(dt.timestamp())
                except:
                    return 0
            return int(timestamp) if timestamp else 0
        
        self._history[address] = [
            tx for tx in self._history[address]
            if get_timestamp_int(tx) >= max_timestamp
        ]

class WindowEvaluator:
    
    def __init__(self, history: Optional[TransactionHistory] = None):
        self.history = history or TransactionHistory()
    
    def evaluate_window_rule(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> bool:
        window_spec = rule.get("window")
        if not window_spec:
            return False
        
        duration_sec = window_spec.get("duration_sec", 0)
        group_by = window_spec.get("group_by", ["address"])
        
        group_key = self._get_group_key(tx_data, group_by)
        if not group_key:
            return False
        
        current_timestamp = self._get_timestamp(tx_data)
        window_txs = self.history.get_window_transactions(
            group_key,
            current_timestamp,
            duration_sec
        )
        
        window_txs.append(tx_data)
        
        aggregations = rule.get("aggregations", [])
        if not aggregations:
            return False
        
        return self._evaluate_aggregations(window_txs, aggregations)
    
    def _get_group_key(
        self,
        tx_data: Dict[str, Any],
        group_by: List[str]
    ) -> Optional[str]:
        if "address" in group_by:
            return tx_data.get("to") or tx_data.get("target_address")
        return None
    
    def _get_timestamp(self, tx_data: Dict[str, Any]) -> int:
        timestamp = tx_data.get("timestamp")
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except:
                return 0
        return int(timestamp) if timestamp else 0
    
    def _evaluate_aggregations(
        self,
        txs: List[Dict[str, Any]],
        aggregations: List[Dict[str, Any]]
    ) -> bool:
        if not txs:
            return False
        
        for agg in aggregations:
            if not self._evaluate_single_aggregation(txs, agg):
                return False
        
        return True
    
    def _evaluate_single_aggregation(
        self,
        txs: List[Dict[str, Any]],
        agg: Dict[str, Any]
    ) -> bool:
        def get_field_value(tx: Dict[str, Any], field: str) -> float:
            if field == "usd_value":
                return float(tx.get("amount_usd", tx.get("usd_value", 0)))
            return float(tx.get(field, 0))
        
        if "sum_gte" in agg:
            spec = agg["sum_gte"]
            field = spec.get("field", "usd_value")
            value = spec.get("value", 0)
            total = sum(get_field_value(tx, field) for tx in txs)
            return total >= float(value)
        
        if "count_gte" in agg:
            value = agg["count_gte"].get("value", 0)
            return len(txs) >= int(value)
        
        if "every_gte" in agg:
            spec = agg["every_gte"]
            field = spec.get("field", "usd_value")
            value = spec.get("value", 0)
            return all(get_field_value(tx, field) >= float(value) for tx in txs)
        
        if "distinct_gte" in agg:
            spec = agg["distinct_gte"]
            field = spec.get("field")
            value = spec.get("value", 0)
            if not field:
                return False
            distinct_values = set(tx.get(field) for tx in txs if tx.get(field))
            return len(distinct_values) >= int(value)
        
        if "any_gte" in agg:
            spec = agg["any_gte"]
            field = spec.get("field", "usd_value")
            value = spec.get("value", 0)
            return any(get_field_value(tx, field) >= float(value) for tx in txs)
        
        if "avg_gte" in agg:
            spec = agg["avg_gte"]
            field = spec.get("field", "usd_value")
            value = spec.get("value", 0)
            if not txs:
                return False
            avg = sum(get_field_value(tx, field) for tx in txs) / len(txs)
            return avg >= float(value)
        
        return False

