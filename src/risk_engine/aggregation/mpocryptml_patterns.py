
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict
from datetime import datetime
import networkx as nx

class MPOCryptoMLPatternDetector:
    
    def __init__(self):
        self.graph: Optional[nx.DiGraph] = None
        self._build_graph()
    
    def _build_graph(self):
        self.graph = nx.DiGraph()
    
    def add_transaction(self, tx: Dict[str, Any]):
        if not self.graph:
            self._build_graph()
        
        from_addr = tx.get("from", "").lower()
        to_addr = tx.get("to", "").lower()
        
        usd_value = float(tx.get("usd_value", tx.get("amount_usd", 0)))
        if usd_value > 0:
            weight = usd_value
        else:
            wei_value = float(tx.get("value", 0))
            if wei_value > 0:
                weight = wei_value / 1e18
            else:
                weight = 0.0
        
        timestamp = tx.get("timestamp", "")
        
        if not from_addr or not to_addr or weight <= 0:
            return
        
        self.graph.add_node(from_addr)
        self.graph.add_node(to_addr)
        
        if self.graph.has_edge(from_addr, to_addr):
            current_weight = self.graph[from_addr][to_addr].get("weight", 0)
            self.graph[from_addr][to_addr]["weight"] = current_weight + weight
            if "transactions" not in self.graph[from_addr][to_addr]:
                self.graph[from_addr][to_addr]["transactions"] = []
            self.graph[from_addr][to_addr]["transactions"].append({
                "tx_hash": tx.get("tx_hash", ""),
                "timestamp": timestamp,
                "usd_value": weight
            })
        else:
            self.graph.add_edge(
                from_addr,
                to_addr,
                weight=weight,
                transactions=[{
                    "tx_hash": tx.get("tx_hash", ""),
                    "timestamp": timestamp,
                    "usd_value": weight
                }]
            )
    
    def build_from_transactions(self, transactions: List[Dict[str, Any]]):
        self._build_graph()
        for tx in transactions:
            self.add_transaction(tx)
    
    def fan_in(self, vertex: str) -> float:
        if not self.graph or vertex.lower() not in self.graph:
            return 0.0
        
        vertex = vertex.lower()
        fan_in_value = 0.0
        
        for predecessor in self.graph.predecessors(vertex):
            edge_weight = self.graph[predecessor][vertex].get("weight", 0)
            fan_in_value += edge_weight
        
        return fan_in_value
    
    def fan_in_count(self, vertex: str) -> int:
        if not self.graph or vertex.lower() not in self.graph:
            return 0
        
        return self.graph.in_degree(vertex.lower())
    
    def fan_out(self, vertex: str) -> float:
        if not self.graph or vertex.lower() not in self.graph:
            return 0.0
        
        vertex = vertex.lower()
        fan_out_value = 0.0
        
        for successor in self.graph.successors(vertex):
            edge_weight = self.graph[vertex][successor].get("weight", 0)
            fan_out_value += edge_weight
        
        return fan_out_value
    
    def fan_out_count(self, vertex: str) -> int:
        if not self.graph or vertex.lower() not in self.graph:
            return 0
        
        return self.graph.out_degree(vertex.lower())
    
    def gather_scatter(self, vertex: str) -> float:
        return self.fan_in(vertex) + self.fan_out(vertex)
    
    def gather_scatter_count(self, vertex: str) -> int:
        return self.fan_in_count(vertex) + self.fan_out_count(vertex)
    
    def detect_fan_in_pattern(
        self,
        vertex: str,
        min_fan_in_count: int = 5,
        min_total_value: float = 0.01,
        min_each_value: float = 0.001
    ) -> Dict[str, Any]:
        if not self.graph or vertex.lower() not in self.graph:
            return {
                "is_detected": False,
                "fan_in_count": 0,
                "total_value": 0.0,
                "sources": [],
                "min_each_value": 0.0
            }
        
        vertex = vertex.lower()
        sources = []
        total_value = 0.0
        min_each = float('inf')
        
        for predecessor in self.graph.predecessors(vertex):
            edge_weight = self.graph[predecessor][vertex].get("weight", 0)
            if edge_weight >= min_each_value:
                sources.append(predecessor)
                total_value += edge_weight
                min_each = min(min_each, edge_weight)
        
        is_detected = (
            len(sources) >= min_fan_in_count and
            total_value >= min_total_value and
            min_each >= min_each_value
        )
        
        return {
            "is_detected": is_detected,
            "fan_in_count": len(sources),
            "total_value": total_value,
            "sources": sources,
            "min_each_value": min_each if min_each != float('inf') else 0.0
        }
    
    def detect_fan_out_pattern(
        self,
        vertex: str,
        min_fan_out_count: int = 5,
        min_total_value: float = 0.01,
        min_each_value: float = 0.001
    ) -> Dict[str, Any]:
        if not self.graph or vertex.lower() not in self.graph:
            return {
                "is_detected": False,
                "fan_out_count": 0,
                "total_value": 0.0,
                "targets": [],
                "min_each_value": 0.0
            }
        
        vertex = vertex.lower()
        targets = []
        total_value = 0.0
        min_each = float('inf')
        
        for successor in self.graph.successors(vertex):
            edge_weight = self.graph[vertex][successor].get("weight", 0)
            if edge_weight >= min_each_value:
                targets.append(successor)
                total_value += edge_weight
                min_each = min(min_each, edge_weight)
        
        is_detected = (
            len(targets) >= min_fan_out_count and
            total_value >= min_total_value and
            min_each >= min_each_value
        )
        
        return {
            "is_detected": is_detected,
            "fan_out_count": len(targets),
            "total_value": total_value,
            "targets": targets,
            "min_each_value": min_each if min_each != float('inf') else 0.0
        }
    
    def detect_stack_pattern(
        self,
        start_vertex: str,
        min_length: int = 3,
        min_path_value: float = 100.0
    ) -> List[Dict[str, Any]]:
        if not self.graph or start_vertex.lower() not in self.graph:
            return []
        
        start_vertex = start_vertex.lower()
        detected_paths = []
        
        def dfs(current: str, path: List[str], visited: Set[str], path_value: float):
            if len(path) >= min_length:
                if path_value >= min_path_value:
                    detected_paths.append({
                        "path": path.copy(),
                        "length": len(path),
                        "total_value": path_value
                    })
            
            if len(path) >= 10:
                return
            
            for successor in self.graph.successors(current):
                if successor not in visited:
                    edge_weight = self.graph[current][successor].get("weight", 0)
                    visited.add(successor)
                    path.append(successor)
                    dfs(successor, path, visited, path_value + edge_weight)
                    path.pop()
                    visited.remove(successor)
        
        dfs(start_vertex, [start_vertex], {start_vertex}, 0.0)
        
        return detected_paths
    
    def detect_bipartite_pattern(
        self,
        vertices: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        if not self.graph:
            return {
                "is_bipartite": False,
                "layer1": set(),
                "layer2": set(),
                "edges_between_layers": 0
            }
        
        if vertices is None:
            vertices = list(self.graph.nodes())
        else:
            vertices = [v.lower() for v in vertices]
        
        try:
            subgraph = self.graph.subgraph(vertices)
            
            undirected = subgraph.to_undirected()
            
            if nx.is_bipartite(undirected):
                layer1, layer2 = nx.bipartite.sets(undirected)
                edges_between = sum(1 for u, v in subgraph.edges() 
                                   if (u in layer1 and v in layer2) or 
                                      (u in layer2 and v in layer1))
                
                return {
                    "is_bipartite": True,
                    "layer1": layer1,
                    "layer2": layer2,
                    "edges_between_layers": edges_between
                }
        except Exception:
            pass
        
        return {
            "is_bipartite": False,
            "layer1": set(),
            "layer2": set(),
            "edges_between_layers": 0
        }
    
    def analyze_address_patterns(self, vertex: str) -> Dict[str, Any]:
        return {
            "fan_in": {
                "value": self.fan_in(vertex),
                "count": self.fan_in_count(vertex),
                "pattern": self.detect_fan_in_pattern(vertex)
            },
            "fan_out": {
                "value": self.fan_out(vertex),
                "count": self.fan_out_count(vertex),
                "pattern": self.detect_fan_out_pattern(vertex)
            },
            "gather_scatter": {
                "value": self.gather_scatter(vertex),
                "count": self.gather_scatter_count(vertex)
            },
            "stack_paths": self.detect_stack_pattern(vertex),
            "bipartite": self.detect_bipartite_pattern([vertex])
        }

