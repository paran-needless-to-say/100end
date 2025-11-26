from __future__ import annotations

from typing import Dict, List, Any, Optional
from src.risk_engine.rules.loader import RuleLoader
from src.risk_engine.data.lists import ListLoader
from src.risk_engine.aggregation.window import WindowEvaluator
from src.risk_engine.aggregation.bucket import BucketEvaluator
from src.risk_engine.aggregation.ppr_connector import PPRConnector
from src.risk_engine.aggregation.mpocryptml_patterns import MPOCryptoMLPatternDetector
from src.risk_engine.aggregation.stats import StatisticsCalculator
from src.risk_engine.aggregation.topology import TopologyEvaluator

class RuleEvaluator:
    
    def __init__(self, rules_path: str = "rules/tracex_rules.yaml", window_evaluator: Optional[WindowEvaluator] = None, bucket_evaluator: Optional[BucketEvaluator] = None):
        self.rule_loader = RuleLoader(rules_path)
        self.list_loader = ListLoader()
        self.ruleset = self.rule_loader.load()
        self.window_evaluator = window_evaluator or WindowEvaluator()
        self.bucket_evaluator = bucket_evaluator or BucketEvaluator()
        self.ppr_connector = PPRConnector()
        self.pattern_detector = None
        self.stats_calculator = StatisticsCalculator()
        self.topology_evaluator = TopologyEvaluator()
    
    def evaluate_single_transaction(
        self,
        tx_data: Dict[str, Any],
        include_topology: bool = False
    ) -> List[Dict[str, Any]]:
        fired_rules = []
        rules = self.rule_loader.get_rules()
        lists = self.list_loader.get_all_lists()
        
        target_address = tx_data.get("to") or tx_data.get("target_address")
        if target_address:
            self.window_evaluator.history.add_transaction(target_address, tx_data)
        
        for rule in rules:
            rule_id = rule.get("id")
            if not rule_id:
                continue
            
            if "state" in rule:
                continue
            
            if rule_id == "E-103":
                conditions = rule.get("conditions", {})
                if not conditions:
                    continue
            
            if rule_id == "E-102":
                if self._evaluate_e102_with_ppr(tx_data, rule, lists):
                    if not self._check_conditions(tx_data, rule, lists):
                        continue
                    if self._check_exceptions(tx_data, rule, lists):
                        continue
                    score = rule.get("score", 30)
                    fired_rules.append({
                        "rule_id": rule_id,
                        "score": float(score),
                        "axis": rule.get("axis", "E"),
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", "HIGH"),
                        "source": "PPR"  # PPR 기반 탐지
                    })
                continue
            
            if rule_id == "B-103":
                if self._evaluate_b103_with_stats(tx_data, rule, lists):
                    if not self._check_conditions(tx_data, rule, lists):
                        continue
                    if self._check_exceptions(tx_data, rule, lists):
                        continue
                    score = rule.get("score", 10)
                    fired_rules.append({
                        "rule_id": rule_id,
                        "score": float(score),
                        "axis": rule.get("axis", "B"),
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", "LOW")
                    })
                continue
            
            if rule_id == "B-201":
                if not include_topology:
                    continue
                if self._evaluate_topology_rule(tx_data, rule, "layering_chain"):
                    if not self._check_conditions(tx_data, rule, lists):
                        continue
                    if self._check_exceptions(tx_data, rule, lists):
                        continue
                    score = rule.get("score", 25)
                    fired_rules.append({
                        "rule_id": rule_id,
                        "score": float(score),
                        "axis": rule.get("axis", "B"),
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", "HIGH")
                    })
                continue
            
            if rule_id == "B-202":
                if not include_topology:
                    continue
                if self._evaluate_topology_rule(tx_data, rule, "cycle"):
                    if not self._check_conditions(tx_data, rule, lists):
                        continue
                    if self._check_exceptions(tx_data, rule, lists):
                        continue
                    score = rule.get("score", 30)
                    fired_rules.append({
                        "rule_id": rule_id,
                        "score": float(score),
                        "axis": rule.get("axis", "B"),
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", "HIGH")
                    })
                continue
            
            has_bucket = "bucket" in rule or "buckets" in rule
            
            if rule_id == "B-501":
                buckets_spec = rule.get("buckets")
                if buckets_spec:
                    field = buckets_spec.get("field", "usd_value")
                    ranges = buckets_spec.get("ranges", [])
                    value = float(tx_data.get(field, 0))
                    
                    dynamic_score = 0
                    for range_spec in ranges:
                        min_val = range_spec.get("min", 0)
                        max_val = range_spec.get("max", float('inf'))
                        if min_val <= value < max_val:
                            dynamic_score = range_spec.get("score", 0)
                            break
                    
                    if dynamic_score > 0:
                        fired_rules.append({
                            "rule_id": rule_id,
                            "score": float(dynamic_score),
                            "axis": rule.get("axis", "B"),
                            "name": rule.get("name", rule_id),
                            "severity": rule.get("severity", "MEDIUM")
                        })
                continue
            
            has_window = "window" in rule or ("aggregations" in rule and not has_bucket)
            
            if has_bucket:
                if not self.bucket_evaluator.evaluate_bucket_rule(tx_data, rule):
                    continue
            elif has_window:
                if not self.window_evaluator.evaluate_window_rule(tx_data, rule):
                    continue
            else:
                if not self._match_rule(tx_data, rule, lists):
                    continue
                
                if not self._check_conditions(tx_data, rule, lists):
                    continue
            
            if self._check_exceptions(tx_data, rule, lists):
                continue
            
            score = rule.get("score", 0)
            if isinstance(score, str):
                try:
                    score = float(score)
                except (ValueError, TypeError):
                    score = 0
            
            fired_rules.append({
                "rule_id": rule_id,
                "score": float(score),
                "axis": rule.get("axis", "B"),
                "name": rule.get("name", rule_id),
                "severity": rule.get("severity", "MEDIUM")
            })
        
        return fired_rules
    
    def _match_rule(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        match_clause = rule.get("match")
        if not match_clause:
            return True
        
        return self._eval_match_clause(tx_data, match_clause, lists)
    
    def _check_conditions(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        conditions = rule.get("conditions")
        if not conditions:
            return True
        
        return self._eval_conditions(tx_data, conditions, lists)
    
    def _check_exceptions(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        exceptions = rule.get("exceptions")
        if not exceptions:
            return False
        
        return self._eval_conditions(tx_data, exceptions, lists)
    
    def _eval_match_clause(
        self,
        tx_data: Dict[str, Any],
        match_clause: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        if "any" in match_clause:
            return any(
                self._eval_single_match(tx_data, item, lists)
                for item in match_clause["any"]
            )
        elif "all" in match_clause:
            return all(
                self._eval_single_match(tx_data, item, lists)
                for item in match_clause["all"]
            )
        else:
            return self._eval_single_match(tx_data, match_clause, lists)
    
    def _eval_single_match(
        self,
        tx_data: Dict[str, Any],
        match_item: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        if "in_list" in match_item:
            spec = match_item["in_list"]
            field = spec.get("field")
            list_name = spec.get("list")
            value = tx_data.get(field, "").lower() if field else ""
            target_list = lists.get(list_name, set())
            
            if value in target_list:
                return True
            
            if list_name == "SDN_LIST" and tx_data.get("is_sanctioned", False):
                return True
            
            if list_name == "MIXER_LIST" and tx_data.get("is_mixer", False):
                return True
            
            return False
        
        return False
    
    def _eval_conditions(
        self,
        tx_data: Dict[str, Any],
        conditions: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        if "all" in conditions:
            return all(
                self._eval_single_condition(tx_data, item, lists)
                for item in conditions["all"]
            )
        elif "any" in conditions:
            return any(
                self._eval_single_condition(tx_data, item, lists)
                for item in conditions["any"]
            )
        else:
            return self._eval_single_condition(tx_data, conditions, lists)
    
    def _evaluate_e102_with_ppr(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        target_address = tx_data.get("to") or tx_data.get("target_address", "")
        if not target_address:
            return False
        
        history = self.window_evaluator.history
        
        address_history = history._history.get(target_address.lower(), [])
        
        if len(address_history) < 2:
            return False
        
        if self.pattern_detector is None:
            self.pattern_detector = MPOCryptoMLPatternDetector()
        else:
            self.pattern_detector._build_graph()
        
        for tx in address_history:
            self.pattern_detector.add_transaction(tx)
        
        self.pattern_detector.add_transaction(tx_data)
        
        if not self.pattern_detector.graph or target_address.lower() not in self.pattern_detector.graph:
            return False
        
        sdn_addresses = lists.get("SDN_LIST", set())
        mixer_addresses = lists.get("MIXER_LIST", set())
        
        ppr_result = self.ppr_connector.calculate_connection_risk(
            target_address,
            self.pattern_detector.graph,
            sdn_addresses,
            mixer_addresses
        )
        
        ppr_threshold = 0.05
        
        return ppr_result["total_ppr"] >= ppr_threshold
    
    def _evaluate_b103_with_stats(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        prerequisites = rule.get("prerequisites", [])
        if prerequisites:
            for prereq in prerequisites:
                if "min_edges" in prereq:
                    min_edges = prereq["min_edges"]
                    target_address = tx_data.get("to") or tx_data.get("target_address", "")
                    if target_address:
                        history = self.window_evaluator.history
                        address_history = history._history.get(target_address.lower(), [])
                        
                        all_transactions = address_history + [tx_data]
                        
                        if not self.stats_calculator.check_prerequisites(all_transactions, min_edges):
                            return False
        
        target_address = tx_data.get("to") or tx_data.get("target_address", "")
        if not target_address:
            return False
        
        history = self.window_evaluator.history
        address_history = history._history.get(target_address.lower(), [])
        
        all_transactions = address_history + [tx_data]
        
        interarrival_std = self.stats_calculator.calculate_interarrival_std(all_transactions)
        
        if interarrival_std is None:
            return False
        
        tx_data["interarrival_std"] = interarrival_std
        
        return True
    
    def _evaluate_topology_rule(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        rule_type: str
    ) -> bool:
        target_address = tx_data.get("to") or tx_data.get("target_address", "")
        if not target_address:
            return False
        
        history = self.window_evaluator.history
        
        address_history = history._history.get(target_address.lower(), [])
        
        all_transactions = address_history + [tx_data]
        
        topology_spec = rule.get("topology", {})
        
        if rule_type == "layering_chain":
            return self.topology_evaluator.evaluate_layering_chain(
                target_address,
                all_transactions,
                topology_spec
            )
        elif rule_type == "cycle":
            return self.topology_evaluator.evaluate_cycle(
                target_address,
                all_transactions,
                topology_spec
            )
        
        return False
    
    def _eval_single_condition(
        self,
        tx_data: Dict[str, Any],
        condition: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        for op in ["gte", "lte", "gt", "lt", "eq"]:
            if op in condition:
                spec = condition[op]
                field = spec.get("field")
                value = spec.get("value")
                tx_value = tx_data.get(field, 0)
                
                if op == "gte":
                    return float(tx_value) >= float(value)
                elif op == "lte":
                    return float(tx_value) <= float(value)
                elif op == "gt":
                    return float(tx_value) > float(value)
                elif op == "lt":
                    return float(tx_value) < float(value)
                elif op == "eq":
                    return tx_value == value
        
        return False

