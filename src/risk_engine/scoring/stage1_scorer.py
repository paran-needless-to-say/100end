from typing import Dict, List, Any, Optional
import numpy as np

from ..rules.evaluator import RuleEvaluator
from .improved_rule_scorer import ImprovedRuleScorer

class Stage1Scorer:
    
    def __init__(
        self,
        rules_path: str = "rules/tracex_rules.yaml",
        rule_weight: float = 0.9,
        graph_weight: float = 0.1
    ):
        self.rule_evaluator = RuleEvaluator(rules_path)
        self.rule_scorer = ImprovedRuleScorer(
            aggregation_method="weighted_sum",
            use_rule_count_bonus=True,
            use_severity_bonus=True,
            use_axis_bonus=True
        )
        self.rule_weight = rule_weight
        self.graph_weight = graph_weight
    
    def calculate_risk_score(
        self,
        tx_data: Dict[str, Any],
        ml_features: Optional[Dict[str, Any]] = None,
        tx_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        rule_results = self.rule_evaluator.evaluate_single_transaction(tx_data)
        
        if tx_context is None:
            tx_context = {}
        if ml_features and "ml_features" not in tx_context:
            tx_context["ml_features"] = ml_features
        
        rule_score = self.rule_scorer.calculate_score(rule_results, tx_context)
        
        graph_score, graph_features_used = self._calculate_graph_score(
            ml_features or {},
            tx_context or {}
        )
        
        final_score = (
            self.rule_weight * rule_score +
            self.graph_weight * graph_score
        )
        final_score = min(100.0, max(0.0, final_score))
        
        explanation = self._generate_explanation(
            rule_score, graph_score, final_score,
            rule_results, graph_features_used
        )
        
        return {
            "risk_score": final_score,
            "rule_score": rule_score,
            "graph_score": graph_score,
            "rule_results": rule_results,
            "graph_features_used": graph_features_used,
            "explanation": explanation
        }
    
    def _calculate_graph_score(
        self,
        ml_features: Dict[str, Any],
        tx_context: Dict[str, Any]
    ) -> tuple[float, Dict[str, Any]]:
        score = 0.0
        features_used = {}
        
        fan_in_count = ml_features.get("fan_in_count", 0)
        fan_out_count = ml_features.get("fan_out_count", 0)
        fan_in_value = ml_features.get("fan_in_value", 0.0)
        fan_out_value = ml_features.get("fan_out_value", 0.0)
        
        tx_fan_in_count = ml_features.get("tx_primary_fan_in_count", fan_in_count)
        tx_fan_out_count = ml_features.get("tx_primary_fan_out_count", fan_out_count)
        tx_fan_in_value = ml_features.get("tx_primary_fan_in_value", fan_in_value)
        tx_fan_out_value = ml_features.get("tx_primary_fan_out_value", fan_out_value)
        
        if tx_fan_in_count < 5:
            score += 10.0
            features_used["low_fan_in"] = tx_fan_in_count
        elif tx_fan_in_count < 10:
            score += 5.0
            features_used["medium_low_fan_in"] = tx_fan_in_count
        
        if tx_fan_out_count >= 25:
            score += 12.0
            features_used["very_high_fan_out"] = tx_fan_out_count
        elif tx_fan_out_count >= 15:
            score += 6.0
            features_used["high_fan_out"] = tx_fan_out_count
        
        if tx_fan_in_value > 1000.0:
            score += 10.0
            features_used["high_fan_in_value"] = tx_fan_in_value
        if tx_fan_out_value > 1000.0:
            score += 10.0
            features_used["high_fan_out_value"] = tx_fan_out_value
        
        pattern_score = ml_features.get("pattern_score", 0.0)
        if pattern_score > 0:
            if pattern_score < 25.0:
                score += 15.0
                features_used["low_pattern_score"] = pattern_score
            elif pattern_score < 30.0:
                score += 8.0
                features_used["medium_low_pattern_score"] = pattern_score
            elif pattern_score > 35.0:
                score -= 5.0
                features_used["high_pattern_score"] = pattern_score
        
        if ml_features.get("fan_in_detected", 0) == 1:
            score += 3.0
            features_used["fan_in_detected"] = True
        if ml_features.get("fan_out_detected", 0) == 1:
            score += 3.0
            features_used["fan_out_detected"] = True
        if ml_features.get("gather_scatter_detected", 0) == 1:
            score += 5.0
            features_used["gather_scatter_detected"] = True
        
        avg_value = ml_features.get("avg_transaction_value", 0.0)
        max_value = ml_features.get("max_transaction_value", 0.0)
        total_value = ml_features.get("total_transaction_value", 0.0)
        
        if avg_value > 50000.0:
            score += 10.0
            features_used["very_high_avg_value"] = avg_value
        elif avg_value > 20000.0:
            score += 5.0
            features_used["high_avg_value"] = avg_value
        
        if max_value > 100000.0:
            score += 8.0
            features_used["very_high_max_value"] = max_value
        elif max_value > 50000.0:
            score += 4.0
            features_used["high_max_value"] = max_value
        
        graph_nodes = tx_context.get("graph_nodes", 0)
        graph_edges = tx_context.get("graph_edges", 0)
        num_transactions = tx_context.get("num_transactions", 0)
        
        if graph_nodes > 120:
            score += 8.0
            features_used["very_large_graph"] = graph_nodes
        elif graph_nodes > 90:
            score += 4.0
            features_used["large_graph"] = graph_nodes
        elif graph_nodes < 70:
            score -= 2.0
            features_used["small_graph"] = graph_nodes
        
        if num_transactions > 100:
            score += 2.0
            features_used["many_transactions"] = num_transactions
        
        ppr_score = ml_features.get("ppr_score", 0.0)
        if ppr_score > 0.5:
            score += 10.0
            features_used["high_ppr"] = ppr_score
        elif ppr_score > 0.3:
            score += 5.0
            features_used["medium_ppr"] = ppr_score
        
        n_theta = ml_features.get("n_theta", 0.0)
        n_omega = ml_features.get("n_omega", 0.0)
        
        if n_theta > 0.85:
            score -= 2.0
            features_used["high_n_theta"] = n_theta
        elif n_theta < 0.80:
            score += 3.0
            features_used["low_n_theta"] = n_theta
        
        if n_omega < 0.45:
            score += 8.0
            features_used["low_n_omega"] = n_omega
        elif n_omega < 0.50:
            score += 4.0
            features_used["medium_low_n_omega"] = n_omega
        elif n_omega > 0.55:
            score -= 3.0
            features_used["high_n_omega"] = n_omega
        
        graph_score = min(100.0, max(0.0, score))
        
        return graph_score, features_used
    
    def _generate_explanation(
        self,
        rule_score: float,
        graph_score: float,
        final_score: float,
        rule_results: List[Dict[str, Any]],
        graph_features_used: Dict[str, Any]
    ) -> str:
        parts = []
        
        if rule_score > 0:
            parts.append(f"Rule-based 점수: {rule_score:.1f}점")
            if rule_results:
                rule_ids = [r.get("rule_id", "") for r in rule_results[:3]]
                parts.append(f"발동된 룰: {', '.join(rule_ids)}")
        
        if graph_score > 0:
            parts.append(f"그래프 통계 점수: {graph_score:.1f}점")
            if graph_features_used:
                feature_names = list(graph_features_used.keys())[:3]
                parts.append(f"주요 feature: {', '.join(feature_names)}")
        
        parts.append(f"최종 Risk Score: {final_score:.1f}점")
        
        return " | ".join(parts)

