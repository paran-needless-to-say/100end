
from typing import Dict, List, Set, Optional, Any
import networkx as nx
from collections import defaultdict

class PPRConnector:
    
    def __init__(self, damping_factor: float = 0.85, max_iter: int = 100):
        self.damping_factor = damping_factor
        self.max_iter = max_iter
    
    def calculate_ppr(
        self,
        target_address: str,
        source_addresses: List[str],
        graph: nx.DiGraph
    ) -> float:
        if not graph or target_address.lower() not in graph:
            return 0.0
        
        target_address = target_address.lower()
        source_addresses = [addr.lower() for addr in source_addresses]
        
        valid_sources = [addr for addr in source_addresses if addr in graph]
        if not valid_sources:
            return 0.0
        
        try:
            personalization = {addr: 1.0 / len(valid_sources) for addr in valid_sources}
            
            for node in graph.nodes():
                if node not in personalization:
                    personalization[node] = 0.0
            
            ppr_scores = nx.pagerank(
                graph,
                alpha=self.damping_factor,
                personalization=personalization,
                max_iter=self.max_iter
            )
            
            return ppr_scores.get(target_address, 0.0)
        
        except Exception:
            return 0.0
    
    def calculate_multi_source_ppr(
        self,
        target_address: str,
        graph: nx.DiGraph,
        auto_detect_sources: bool = True
    ) -> Dict[str, Any]:
        if not graph or target_address.lower() not in graph:
            return {
                "ppr_score": 0.0,
                "source_nodes": [],
                "visited_nodes": []
            }
        
        target_address = target_address.lower()
        
        if auto_detect_sources:
            source_nodes = [
                node for node in graph.nodes()
                if graph.out_degree(node) > 0 and graph.in_degree(node) == 0
            ]
        else:
            source_nodes = []
        
        if not source_nodes:
            return {
                "ppr_score": 0.0,
                "source_nodes": [],
                "visited_nodes": []
            }
        
        ppr_score = self.calculate_ppr(target_address, source_nodes, graph)
        
        try:
            personalization = {addr: 1.0 / len(source_nodes) for addr in source_nodes}
            for node in graph.nodes():
                if node not in personalization:
                    personalization[node] = 0.0
            
            ppr_scores = nx.pagerank(
                graph,
                alpha=self.damping_factor,
                personalization=personalization,
                max_iter=self.max_iter
            )
            
            visited_nodes = [
                node for node, score in ppr_scores.items()
                if score > 0.001
            ]
        except:
            visited_nodes = []
        
        return {
            "ppr_score": ppr_score,
            "source_nodes": source_nodes,
            "visited_nodes": visited_nodes
        }
    
    def calculate_connection_risk(
        self,
        target_address: str,
        graph: nx.DiGraph,
        sdn_addresses: Set[str],
        mixer_addresses: Set[str]
    ) -> Dict[str, Any]:
        sdn_list = [addr.lower() for addr in sdn_addresses if addr.lower() in graph]
        mixer_list = [addr.lower() for addr in mixer_addresses if addr.lower() in graph]
        
        sdn_ppr = 0.0
        mixer_ppr = 0.0
        
        if sdn_list:
            sdn_ppr = self.calculate_ppr(target_address, sdn_list, graph)
        
        if mixer_list:
            mixer_ppr = self.calculate_ppr(target_address, mixer_list, graph)
        
        total_ppr = (sdn_ppr * 0.6 + mixer_ppr * 0.4)
        
        if total_ppr >= 0.1:
            risk_level = "high"
        elif total_ppr >= 0.05:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "sdn_ppr": sdn_ppr,
            "mixer_ppr": mixer_ppr,
            "total_ppr": total_ppr,
            "risk_level": risk_level
        }

