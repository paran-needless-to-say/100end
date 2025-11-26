
from typing import Dict, List, Set, Optional, Any
import networkx as nx
from collections import defaultdict

from .mpocryptml_patterns import MPOCryptoMLPatternDetector
from .ppr_connector import PPRConnector
from .mpocryptml_normalizer import MPOCryptoMLNormalizer

class MPOCryptoMLScorer:
    
    def __init__(
        self,
        damping_factor: float = 0.85,
        max_iter: int = 1000,
        rule_weight: float = 0.7,
        ml_weight: float = 0.3
    ):
        self.pattern_detector = MPOCryptoMLPatternDetector()
        self.ppr_connector = PPRConnector(damping_factor=damping_factor, max_iter=max_iter)
        self.normalizer = MPOCryptoMLNormalizer()
        self.rule_weight = rule_weight
        self.ml_weight = ml_weight
    
    def build_graph_from_transactions(
        self,
        transactions: List[Dict[str, Any]]
    ) -> nx.DiGraph:
        self.pattern_detector.build_from_transactions(transactions)
        return self.pattern_detector.graph
    
    def calculate_ppr_score(
        self,
        target_address: str,
        graph: nx.DiGraph,
        source_addresses: Optional[List[str]] = None,
        sdn_addresses: Optional[Set[str]] = None,
        mixer_addresses: Optional[Set[str]] = None
    ) -> Dict[str, float]:
        if not graph or target_address.lower() not in graph:
            return {
                "ppr_score": 0.0,
                "sdn_ppr": 0.0,
                "mixer_ppr": 0.0,
                "total_ppr": 0.0
            }
        
        if source_addresses is None:
            source_addresses = [
                node for node in graph.nodes()
                if graph.out_degree(node) > 0 and graph.in_degree(node) == 0
            ]
        
        sdn_ppr = 0.0
        mixer_ppr = 0.0
        
        if sdn_addresses:
            sdn_list = [addr for addr in sdn_addresses if addr.lower() in graph]
            if sdn_list:
                sdn_ppr = self.ppr_connector.calculate_ppr(
                    target_address, sdn_list, graph
                )
        
        if mixer_addresses:
            mixer_list = [addr for addr in mixer_addresses if addr.lower() in graph]
            if mixer_list:
                mixer_ppr = self.ppr_connector.calculate_ppr(
                    target_address, mixer_list, graph
                )
        
        if source_addresses:
            ppr_score = self.ppr_connector.calculate_ppr(
                target_address, source_addresses, graph
            )
        else:
            ppr_score = 0.0
        
        total_ppr = ppr_score * 0.4 + sdn_ppr * 0.4 + mixer_ppr * 0.2
        
        return {
            "ppr_score": ppr_score,
            "sdn_ppr": sdn_ppr,
            "mixer_ppr": mixer_ppr,
            "total_ppr": total_ppr
        }
    
    def calculate_pattern_score(
        self,
        target_address: str,
        graph: nx.DiGraph
    ) -> Dict[str, Any]:
        patterns = self.pattern_detector.analyze_address_patterns(target_address)
        
        pattern_score = 0.0
        detected_patterns = []
        
        if patterns["fan_in"]["pattern"]["is_detected"]:
            pattern_score += 15.0
            detected_patterns.append("fan_in")
        
        if patterns["fan_out"]["pattern"]["is_detected"]:
            pattern_score += 15.0
            detected_patterns.append("fan_out")
        
        if (patterns["fan_in"]["pattern"]["is_detected"] and
            patterns["fan_out"]["pattern"]["is_detected"]):
            pattern_score += 10.0
            detected_patterns.append("gather_scatter")
        
        if patterns["stack_paths"]:
            pattern_score += 20.0
            detected_patterns.append("stack")
        
        if patterns["bipartite"]["is_bipartite"]:
            pattern_score += 15.0
            detected_patterns.append("bipartite")
        
        return {
            "pattern_score": min(100.0, pattern_score),
            "detected_patterns": detected_patterns,
            "patterns": patterns
        }
    
    def calculate_ml_score(
        self,
        target_address: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]],
        sdn_addresses: Optional[Set[str]] = None,
        mixer_addresses: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        ppr_result = self.calculate_ppr_score(
            target_address, graph, None, sdn_addresses, mixer_addresses
        )
        ppr_score = ppr_result["total_ppr"] * 100  # 0~1 -> 0~100
        
        pattern_result = self.calculate_pattern_score(target_address, graph)
        pattern_score = pattern_result["pattern_score"]
        
        n_theta = self.normalizer.normalize_timestamp(
            target_address, graph, transactions
        )
        nts_score = n_theta * 20
        
        n_omega = self.normalizer.normalize_weight(
            target_address, graph, transactions
        )
        nws_score = n_omega * 20
        
        ml_score = (
            ppr_score * 0.3 +
            pattern_score * 0.4 +
            nts_score * 0.15 +
            nws_score * 0.15
        )
        
        return {
            "ml_score": min(100.0, ml_score),
            "ppr_score": ppr_score,
            "pattern_score": pattern_score,
            "nts_score": nts_score,
            "nws_score": nws_score,
            "n_theta": n_theta,
            "n_omega": n_omega,
            "details": {
                "ppr": ppr_result,
                "patterns": pattern_result,
                "detected_patterns": pattern_result["detected_patterns"]
            }
        }
    
    def calculate_hybrid_score(
        self,
        rule_based_score: float,
        target_address: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]],
        sdn_addresses: Optional[Set[str]] = None,
        mixer_addresses: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        ml_result = self.calculate_ml_score(
            target_address, graph, transactions, sdn_addresses, mixer_addresses
        )
        ml_score = ml_result["ml_score"]
        
        final_score = (
            rule_based_score * self.rule_weight +
            ml_score * self.ml_weight
        )
        
        return {
            "final_score": min(100.0, final_score),
            "rule_score": rule_based_score,
            "ml_score": ml_score,
            "ml_details": ml_result
        }

