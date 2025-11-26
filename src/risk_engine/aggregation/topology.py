
from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
import networkx as nx

from .mpocryptml_patterns import MPOCryptoMLPatternDetector

class TopologyEvaluator:
    
    def __init__(self):
        self.pattern_detector = MPOCryptoMLPatternDetector()
    
    def evaluate_layering_chain(
        self,
        target_address: str,
        transactions: List[Dict[str, Any]],
        rule_spec: Dict[str, Any]
    ) -> bool:
        same_token = rule_spec.get("same_token", False)
        hop_length_gte = rule_spec.get("hop_length_gte", 3)
        hop_amount_delta_pct_lte = rule_spec.get("hop_amount_delta_pct_lte", 5)
        min_usd_value = rule_spec.get("min_usd_value", 100)
        
        self.pattern_detector._build_graph()
        for tx in transactions:
            self.pattern_detector.add_transaction(tx)
        
        if not self.pattern_detector.graph:
            return False
        
        target_address = target_address.lower()
        
        if same_token:
            token_graphs = self._build_token_graphs(transactions)
            for token, graph in token_graphs.items():
                if self._find_layering_chain_in_graph(
                    target_address,
                    graph,
                    hop_length_gte,
                    hop_amount_delta_pct_lte,
                    min_usd_value
                ):
                    return True
        else:
            if self._find_layering_chain_in_graph(
                target_address,
                self.pattern_detector.graph,
                hop_length_gte,
                hop_amount_delta_pct_lte,
                min_usd_value
            ):
                return True
        
        return False
    
    def evaluate_cycle(
        self,
        target_address: str,
        transactions: List[Dict[str, Any]],
        rule_spec: Dict[str, Any]
    ) -> bool:
        same_token = rule_spec.get("same_token", False)
        cycle_length_in = rule_spec.get("cycle_length_in", [2, 3])
        cycle_total_usd_gte = rule_spec.get("cycle_total_usd_gte", 100)
        
        self.pattern_detector._build_graph()
        for tx in transactions:
            self.pattern_detector.add_transaction(tx)
        
        if not self.pattern_detector.graph:
            return False
        
        target_address = target_address.lower()
        
        if same_token:
            token_graphs = self._build_token_graphs(transactions)
            for token, graph in token_graphs.items():
                if self._find_cycle_in_graph(
                    target_address,
                    graph,
                    cycle_length_in,
                    cycle_total_usd_gte
                ):
                    return True
        else:
            if self._find_cycle_in_graph(
                target_address,
                self.pattern_detector.graph,
                cycle_length_in,
                cycle_total_usd_gte
            ):
                return True
        
        return False
    
    def _build_token_graphs(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, nx.DiGraph]:
        token_graphs: Dict[str, nx.DiGraph] = defaultdict(lambda: nx.DiGraph())
        
        for tx in transactions:
            token = tx.get("asset_contract", "").lower()
            from_addr = (tx.get("from") or tx.get("counterparty_address", "")).lower()
            to_addr = (tx.get("to") or tx.get("target_address", "")).lower()
            weight = float(tx.get("usd_value", tx.get("amount_usd", 0)))
            
            if not from_addr or not to_addr:
                continue
            
            token_graphs[token].add_node(from_addr)
            token_graphs[token].add_node(to_addr)
            
            if token_graphs[token].has_edge(from_addr, to_addr):
                current_weight = token_graphs[token][from_addr][to_addr].get("weight", 0)
                token_graphs[token][from_addr][to_addr]["weight"] = current_weight + weight
            else:
                token_graphs[token].add_edge(from_addr, to_addr, weight=weight)
        
        return dict(token_graphs)
    
    def _find_layering_chain_in_graph(
        self,
        start_address: str,
        graph: nx.DiGraph,
        min_hops: int,
        max_amount_delta_pct: float,
        min_usd_value: float
    ) -> bool:
        if start_address not in graph:
            return False
        
        def dfs(current: str, path: List[str], path_weights: List[float], visited: Set[str]):
            if len(path) >= min_hops + 1:
                if self._check_amount_delta(path_weights, max_amount_delta_pct):
                    return True
            
            if len(path) >= 10:
                return False
            
            for successor in graph.successors(current):
                if successor in visited:
                    continue
                
                edge_weight = graph[current][successor].get("weight", 0)
                if edge_weight < min_usd_value:
                    continue
                
                visited.add(successor)
                path.append(successor)
                path_weights.append(edge_weight)
                
                if dfs(successor, path, path_weights, visited):
                    return True
                
                path.pop()
                path_weights.pop()
                visited.remove(successor)
            
            return False
        
        return dfs(start_address, [start_address], [], {start_address})
    
    def _find_cycle_in_graph(
        self,
        target_address: str,
        graph: nx.DiGraph,
        cycle_lengths: List[int],
        min_total_usd: float
    ) -> bool:
        if target_address not in graph:
            return False
        
        try:
            for cycle_length in cycle_lengths:
                if self._find_cycle_of_length(target_address, graph, cycle_length, min_total_usd):
                    return True
        except Exception:
            pass
        
        return False
    
    def _find_cycle_of_length(
        self,
        start_address: str,
        graph: nx.DiGraph,
        cycle_length: int,
        min_total_usd: float
    ) -> bool:
        def dfs(current: str, path: List[str], path_weights: List[float], visited: Set[str]):
            if len(path) == cycle_length + 1:
                if path[-1] == start_address:
                    total_usd = sum(path_weights)
                    if total_usd >= min_total_usd:
                        return True
                return False
            
            if len(path) > cycle_length + 1:
                return False
            
            for successor in graph.successors(current):
                if len(path) == cycle_length:
                    if successor != start_address:
                        continue
                elif successor in visited:
                    continue
                
                edge_weight = graph[current][successor].get("weight", 0)
                
                visited.add(successor)
                path.append(successor)
                path_weights.append(edge_weight)
                
                if dfs(successor, path, path_weights, visited):
                    return True
                
                path.pop()
                path_weights.pop()
                visited.remove(successor)
            
            return False
        
        return dfs(start_address, [start_address], [], {start_address})
    
    def _check_amount_delta(
        self,
        amounts: List[float],
        max_delta_pct: float
    ) -> bool:
        if len(amounts) < 2:
            return True
        
        base_amount = amounts[0]
        
        for amount in amounts[1:]:
            if base_amount == 0:
                return False
            
            delta_pct = abs(amount - base_amount) / base_amount * 100
            if delta_pct > max_delta_pct:
                return False
        
        return True

