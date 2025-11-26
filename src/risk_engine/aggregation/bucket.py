
from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta

class BucketEvaluator:
    
    def __init__(self, max_history_days: int = 365):
        self.max_history_days = max_history_days
        self._buckets: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    
    def add_transaction(self, tx: Dict[str, Any], bucket_spec: Dict[str, Any]):
        size_sec = bucket_spec.get("size_sec", 600)  # 기본 10분
        group_fields = bucket_spec.get("group", [])
        
        group_key = self._get_group_key(tx, group_fields)
        if not group_key:
            return
        
        bucket_key = self._get_bucket_key(tx, size_sec)
        if not bucket_key:
            return
        
        self._buckets[group_key][bucket_key].append(tx)
        
        self._cleanup_old_buckets(group_key, bucket_key, size_sec)
    
    def _get_group_key(self, tx: Dict[str, Any], group_fields: List[str]) -> Optional[str]:
        if not group_fields:
            return None
        
        key_parts = []
        for field in group_fields:
            if field == "bucket_10m":
                continue
            value = tx.get(field, "")
            if value:
                key_parts.append(str(value).lower())
        
        return "_".join(key_parts) if key_parts else None
    
    def _get_bucket_key(self, tx: Dict[str, Any], size_sec: int) -> Optional[str]:
        timestamp = self._get_timestamp_int(tx)
        if not timestamp:
            return None
        
        bucket_start = (timestamp // size_sec) * size_sec
        return str(bucket_start)
    
    def _get_timestamp_int(self, tx: Dict[str, Any]) -> Optional[int]:
        timestamp = tx.get("timestamp", 0)
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except:
                return None
        return int(timestamp) if timestamp else None
    
    def _cleanup_old_buckets(self, group_key: str, current_bucket_key: str, size_sec: int):
        max_timestamp = int(datetime.now().timestamp()) - (self.max_history_days * 86400)
        current_bucket_start = int(current_bucket_key)
        max_bucket_start = (max_timestamp // size_sec) * size_sec
        
        buckets_to_remove = []
        for bucket_key in self._buckets[group_key].keys():
            bucket_start = int(bucket_key)
            if bucket_start < max_bucket_start:
                buckets_to_remove.append(bucket_key)
        
        for bucket_key in buckets_to_remove:
            del self._buckets[group_key][bucket_key]
    
    def get_bucket_transactions(
        self,
        tx: Dict[str, Any],
        bucket_spec: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        size_sec = bucket_spec.get("size_sec", 600)
        group_fields = bucket_spec.get("group", [])
        
        group_key = self._get_group_key(tx, group_fields)
        bucket_key = self._get_bucket_key(tx, size_sec)
        
        if not group_key or not bucket_key:
            return []
        
        return self._buckets[group_key].get(bucket_key, [])
    
    def evaluate_bucket_rule(
        self,
        tx: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> bool:
        bucket_spec = rule.get("bucket")
        if not bucket_spec:
            return False
        
        self.add_transaction(tx, bucket_spec)
        
        bucket_txs = self.get_bucket_transactions(tx, bucket_spec)
        
        if tx not in bucket_txs:
            bucket_txs.append(tx)
        
        aggregations = rule.get("aggregations", [])
        if not aggregations:
            return False
        
        return self._evaluate_aggregations(bucket_txs, aggregations)
    
    def _evaluate_aggregations(
        self,
        txs: List[Dict[str, Any]],
        aggregations: List[Dict[str, Any]]
    ) -> bool:
        from src.risk_engine.aggregation.window import WindowEvaluator
        
        window_eval = WindowEvaluator()
        return window_eval._evaluate_aggregations(txs, aggregations)

