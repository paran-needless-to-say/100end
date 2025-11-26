
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
import networkx as nx
import numpy as np

class MPOCryptoMLNormalizer:
    
    def __init__(self):
        pass
    
    def normalize_timestamp(
        self,
        vertex: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]]
    ) -> float:
        if not graph or vertex.lower() not in graph:
            return 0.0
        
        vertex = vertex.lower()
        
        ts_in = []
        for predecessor in graph.predecessors(vertex):
            edge_data = graph[predecessor][vertex]
            if "transactions" in edge_data:
                for tx in edge_data["transactions"]:
                    ts = self._extract_timestamp(tx.get("timestamp"))
                    if ts > 0:
                        ts_in.append(ts)
        
        ts_out = []
        for successor in graph.successors(vertex):
            edge_data = graph[vertex][successor]
            if "transactions" in edge_data:
                for tx in edge_data["transactions"]:
                    ts = self._extract_timestamp(tx.get("timestamp"))
                    if ts > 0:
                        ts_out.append(ts)
        
        if not ts_in or not ts_out:
            ts_in, ts_out = self._extract_timestamps_from_transactions(
                vertex, transactions
            )
        
        if not ts_in or not ts_out:
            return 0.0
        
        ts_in_spread = max(ts_in) - min(ts_in) if len(ts_in) > 1 else 0
        ts_out_spread = max(ts_out) - min(ts_out) if len(ts_out) > 1 else 0
        
        ts_in_avg = np.mean(ts_in)
        ts_out_avg = np.mean(ts_out)
        
        time_diff = abs(ts_out_avg - ts_in_avg)
        
        if ts_in_spread + ts_out_spread > 0:
            normalized_diff = time_diff / (ts_in_spread + ts_out_spread + 1)
        else:
            normalized_diff = min(1.0, time_diff / 86400)
        
        n_theta = 1.0 - min(1.0, normalized_diff)
        
        return n_theta
    
    def normalize_weight(
        self,
        vertex: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]]
    ) -> float:
        if not graph or vertex.lower() not in graph:
            return 0.0
        
        vertex = vertex.lower()
        
        weights_in = []
        for predecessor in graph.predecessors(vertex):
            edge_data = graph[predecessor][vertex]
            weight = edge_data.get("weight", 0)
            if weight > 0:
                weights_in.append(weight)
        
        weights_out = []
        for successor in graph.successors(vertex):
            edge_data = graph[vertex][successor]
            weight = edge_data.get("weight", 0)
            if weight > 0:
                weights_out.append(weight)
        
        if not weights_in or not weights_out:
            weights_in, weights_out = self._extract_weights_from_transactions(
                vertex, transactions
            )
        
        if not weights_in or not weights_out:
            return 0.0
        
        total_in = sum(weights_in)
        total_out = sum(weights_out)
        
        avg_in = np.mean(weights_in) if weights_in else 0
        avg_out = np.mean(weights_out) if weights_out else 0
        
        if total_in + total_out > 0:
            ratio_in = total_in / (total_in + total_out)
            ratio_out = total_out / (total_in + total_out)
            
            imbalance = abs(ratio_in - ratio_out)
        else:
            imbalance = 0.0
        
        if avg_in + avg_out > 0:
            avg_imbalance = abs(avg_in - avg_out) / (avg_in + avg_out)
        else:
            avg_imbalance = 0.0
        
        n_omega = (imbalance + avg_imbalance) / 2.0
        
        return min(1.0, n_omega)
    
    def _extract_timestamp(self, timestamp: Any) -> int:
        if isinstance(timestamp, int):
            return timestamp
        elif isinstance(timestamp, str):
            try:
                from datetime import datetime
                if 'T' in timestamp or ' ' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    return int(dt.timestamp())
                else:
                    return int(timestamp)
            except:
                return 0
        return 0
    
    def _extract_timestamps_from_transactions(
        self,
        vertex: str,
        transactions: List[Dict[str, Any]]
    ) -> Tuple[List[int], List[int]]:
        vertex = vertex.lower()
        ts_in = []
        ts_out = []
        
        for tx in transactions:
            from_addr = (tx.get("from") or tx.get("counterparty_address", "")).lower()
            to_addr = (tx.get("to") or tx.get("target_address", "")).lower()
            ts = self._extract_timestamp(tx.get("timestamp"))
            
            if ts > 0:
                if to_addr == vertex:
                    ts_in.append(ts)
                elif from_addr == vertex:
                    ts_out.append(ts)
        
        return ts_in, ts_out
    
    def _extract_weights_from_transactions(
        self,
        vertex: str,
        transactions: List[Dict[str, Any]]
    ) -> Tuple[List[float], List[float]]:
        vertex = vertex.lower()
        weights_in = []
        weights_out = []
        
        for tx in transactions:
            from_addr = (tx.get("from") or tx.get("counterparty_address", "")).lower()
            to_addr = (tx.get("to") or tx.get("target_address", "")).lower()
            
            usd_value = float(tx.get("usd_value", tx.get("amount_usd", 0)))
            if usd_value > 0:
                weight = usd_value
            else:
                wei_value = float(tx.get("value", 0))
                if wei_value > 0:
                    weight = wei_value / 1e18
                else:
                    continue
            
            if weight > 0:
                if to_addr == vertex:
                    weights_in.append(weight)
                elif from_addr == vertex:
                    weights_out.append(weight)
        
        return weights_in, weights_out
    
    def calculate_feature_vector(
        self,
        vertex: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        n_theta = self.normalize_timestamp(vertex, graph, transactions)
        n_omega = self.normalize_weight(vertex, graph, transactions)
        
        feature_vector = [n_theta, n_omega]
        
        return {
            "n_theta": n_theta,
            "n_omega": n_omega,
            "feature_vector": feature_vector
        }

