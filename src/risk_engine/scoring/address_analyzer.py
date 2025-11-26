from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict

from ..rules.evaluator import RuleEvaluator
from ..aggregation.window import WindowEvaluator, TransactionHistory

@dataclass
class AddressAnalysisResult:
    address: str
    chain: str
    risk_score: float
    risk_level: str
    analysis_summary: Dict[str, Any]
    fired_rules: List[Dict[str, Any]]
    risk_tags: List[str]
    transaction_patterns: Dict[str, Any]
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""  # 리스크 스코어 설명
    completed_at: str = ""  # ISO8601 UTC 형식의 스코어링 완료 시각

class AddressAnalyzer:
    
    def __init__(self, rules_path: str = "rules/tracex_rules.yaml"):
        self.history = TransactionHistory()
        window_evaluator = WindowEvaluator(self.history)
        
        self.rule_evaluator = RuleEvaluator(rules_path, window_evaluator)
    
    def analyze_address(
        self,
        address: str,
        chain: str,
        transactions: List[Dict[str, Any]],
        time_range: Optional[Dict[str, str]] = None,
        analysis_type: str = "basic"  # "basic" or "advanced"
    ) -> AddressAnalysisResult:
        if not transactions:
            return self._empty_result(address, chain)
        
        sorted_txs = sorted(
            transactions,
            key=lambda tx: self._get_timestamp(tx)
        )
        
        all_fired_rules = []
        transaction_scores = []
        timeline = []
        
        include_topology = (analysis_type == "advanced")
        
        for tx in sorted_txs:
            tx_data = self._convert_transaction(tx, address)
            
            fired_rules = self.rule_evaluator.evaluate_single_transaction(
                tx_data,
                include_topology=include_topology
            )
            
            def safe_get_score(rule: Dict[str, Any]) -> float:
                score = rule.get("score", 0)
                if isinstance(score, (int, float)):
                    return float(score)
                if isinstance(score, str):
                    try:
                        return float(score)
                    except (ValueError, TypeError):
                        return 0.0
                return 0.0
            
            tx_score = sum(safe_get_score(r) for r in fired_rules)
            transaction_scores.append(tx_score)
            
            all_fired_rules.extend(fired_rules)
            
            timeline.append({
                "timestamp": tx.get("timestamp"),
                "tx_hash": tx.get("tx_hash"),
                "risk_score": min(100.0, tx_score),
                "fired_rules": [r["rule_id"] for r in fired_rules]
            })
        
        final_score = self._calculate_final_score(transaction_scores, sorted_txs)
        
        risk_level = self._determine_risk_level(final_score)
        
        aggregated_rules = self._aggregate_rules(all_fired_rules)
        
        risk_tags = self._generate_risk_tags(aggregated_rules)
        
        patterns = self._analyze_patterns(sorted_txs, all_fired_rules)
        
        summary = self._create_summary(sorted_txs, time_range)
        
        explanation = self._generate_explanation(
            aggregated_rules, risk_tags, final_score, risk_level
        )
        
        completed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        return AddressAnalysisResult(
            address=address,
            chain=chain,
            risk_score=final_score,
            risk_level=risk_level,
            analysis_summary=summary,
            fired_rules=aggregated_rules,
            risk_tags=risk_tags,
            transaction_patterns=patterns,
            timeline=timeline,
            explanation=explanation,
            completed_at=completed_at
        )
    
    def _convert_transaction(
        self,
        tx: Dict[str, Any],
        target_address: str
    ) -> Dict[str, Any]:
        from_addr = tx.get("from") or tx.get("counterparty_address", "")
        to_addr = tx.get("to") or tx.get("target_address", target_address)
        
        return {
            "from": from_addr,
            "to": to_addr,
            "target_address": target_address,
            "tx_hash": tx.get("tx_hash", ""),
            "timestamp": tx.get("timestamp", ""),
            "usd_value": tx.get("amount_usd", 0.0),
            "chain": tx.get("chain", ""),
            "block_height": tx.get("block_height", 0),
            "is_sanctioned": tx.get("is_sanctioned", False),
            "is_known_scam": tx.get("is_known_scam", False),
            "is_mixer": tx.get("is_mixer", False),
            "is_bridge": tx.get("is_bridge", False),
            "label": tx.get("label", tx.get("entity_type", "unknown")),  # entity_type -> label로 변경
            "asset_contract": tx.get("asset_contract", ""),
        }
    
    def _get_timestamp(self, tx: Dict[str, Any]) -> int:
        timestamp = tx.get("timestamp")
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except:
                return 0
        return int(timestamp) if timestamp else 0
    
    def _calculate_final_score(
        self,
        transaction_scores: List[float],
        transactions: List[Dict[str, Any]]
    ) -> float:
        if not transaction_scores:
            return 0.0
        
        max_score = max(transaction_scores)
        
        if len(transactions) > 1:
            recent_weight = 0.7
            old_weight = 0.3
            
            recent_count = max(1, int(len(transaction_scores) * 0.3))
            recent_scores = transaction_scores[-recent_count:]
            old_scores = transaction_scores[:-recent_count]
            
            recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else 0
            old_avg = sum(old_scores) / len(old_scores) if old_scores else 0
            
            weighted_avg = recent_avg * recent_weight + old_avg * old_weight
            
            return min(100.0, max(max_score, weighted_avg))
        
        return min(100.0, max_score)
    
    def _determine_risk_level(self, score: float) -> str:
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 30:
            return "medium"
        else:
            return "low"
    
    def _aggregate_rules(
        self,
        all_fired_rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        rule_counts = defaultdict(lambda: {
            "count": 0,
            "score": 0,
            "axis": "",
            "name": "",
            "severity": ""
        })
        
        for rule in all_fired_rules:
            rule_id = rule.get("rule_id")
            if not rule_id:
                continue
            
            rule_counts[rule_id]["count"] += 1
            rule_counts[rule_id]["score"] = rule.get("score", 0)
            rule_counts[rule_id]["axis"] = rule.get("axis", "B")
            rule_counts[rule_id]["name"] = rule.get("name", rule_id)
            rule_counts[rule_id]["severity"] = rule.get("severity", "MEDIUM")
        
        return [
            {
                "rule_id": rule_id,
                "score": int(info["score"])  # 정수로 변환
            }
            for rule_id, info in rule_counts.items()
        ]
    
    def _generate_risk_tags(
        self,
        aggregated_rules: List[Dict[str, Any]]
    ) -> List[str]:
        tags = set()
        
        from ..rules.loader import RuleLoader
        rule_loader = RuleLoader()
        rules = rule_loader.get_rules()
        rule_map = {rule.get("id"): rule.get("name", rule.get("id")) for rule in rules if rule.get("id")}
        
        for rule in aggregated_rules:
            rule_id = rule.get("rule_id", "")
            rule_name = rule_map.get(rule_id, "").lower()
            
            if "mixer" in rule_name or "E-101" in rule_id:
                tags.add("mixer_inflow")
            if "sanction" in rule_name or "C-001" in rule_id:
                tags.add("sanction_exposure")
            if "scam" in rule_name:
                tags.add("scam_exposure")
            if "high-value" in rule_name or "C-003" in rule_id or "C-004" in rule_id:
                tags.add("high_value_transfer")
            if "bridge" in rule_name:
                tags.add("bridge_large_transfer")
            if "cex" in rule_name:
                tags.add("cex_inflow")
            if "burst" in rule_name or "B-101" in rule_id or "B-102" in rule_id:
                tags.add("suspicious_pattern")
        
        return sorted(list(tags))
    
    def _analyze_patterns(
        self,
        transactions: List[Dict[str, Any]],
        fired_rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        patterns = {
            "mixer_exposure_count": 0,
            "sanctioned_exposure_count": 0,
            "high_value_count": 0,
            "burst_patterns": 0,
            "total_volume_usd": 0.0
        }
        
        for tx in transactions:
            if tx.get("is_mixer"):
                patterns["mixer_exposure_count"] += 1
            if tx.get("is_sanctioned"):
                patterns["sanctioned_exposure_count"] += 1
            if tx.get("amount_usd", 0) >= 1000:
                patterns["high_value_count"] += 1
            patterns["total_volume_usd"] += tx.get("amount_usd", 0.0)
        
        for rule in fired_rules:
            rule_id = rule.get("rule_id", "")
            if "B-101" in rule_id or "B-102" in rule_id:
                patterns["burst_patterns"] += 1
        
        return patterns
    
    def _generate_explanation(
        self,
        aggregated_rules: List[Dict[str, Any]],
        risk_tags: List[str],
        risk_score: float,
        risk_level: str
    ) -> str:
        if not aggregated_rules:
            return "정상 거래 패턴으로 리스크가 낮습니다."
        
        from ..rules.loader import RuleLoader
        rule_loader = RuleLoader()
        rules = rule_loader.get_rules()
        rule_map = {rule.get("id"): rule.get("name", rule.get("id")) for rule in rules if rule.get("id")}
        
        sorted_rules = sorted(
            aggregated_rules,
            key=lambda x: x.get("score", 0),
            reverse=True
        )
        
        explanations = []
        
        mixer_rules = [r for r in sorted_rules if "E-101" in r.get("rule_id", "")]
        if mixer_rules:
            rule_id = mixer_rules[0].get("rule_id", "")
            rule_name = rule_map.get(rule_id, rule_id)
            explanations.append(f"{rule_name} 패턴 감지")
        
        sanction_rules = [r for r in sorted_rules if "C-001" in r.get("rule_id", "")]
        if sanction_rules:
            rule_id = sanction_rules[0].get("rule_id", "")
            rule_name = rule_map.get(rule_id, rule_id)
            explanations.append(f"{rule_name} 패턴 감지")
        
        high_value_rules = [r for r in sorted_rules if "C-003" in r.get("rule_id", "")]
        if high_value_rules:
            rule_id = high_value_rules[0].get("rule_id", "")
            rule_name = rule_map.get(rule_id, rule_id)
            explanations.append(f"{rule_name} 패턴 감지")
        
        repeated_rules = [r for r in sorted_rules if "C-004" in r.get("rule_id", "")]
        if repeated_rules:
            rule_id = repeated_rules[0].get("rule_id", "")
            rule_name = rule_map.get(rule_id, rule_id)
            explanations.append(f"{rule_name} 패턴 감지")
        
        burst_rules = [r for r in sorted_rules if "B-101" in r.get("rule_id", "")]
        if burst_rules:
            rule_id = burst_rules[0].get("rule_id", "")
            rule_name = rule_map.get(rule_id, rule_id)
            explanations.append(f"{rule_name} 패턴 감지")
        
        if not explanations:
            top_rule = sorted_rules[0] if sorted_rules else None
            if top_rule:
                rule_id = top_rule.get("rule_id", "")
                rule_name = rule_map.get(rule_id, rule_id)
                explanations.append(f"{rule_name} 룰 발동")
        
        if explanations:
            explanation_text = ", ".join(explanations)
            if risk_level == "high" or risk_level == "critical":
                explanation_text += f"로 인해 {risk_level} 리스크로 분류됨."
            elif risk_level == "medium":
                explanation_text += f"로 인해 {risk_level} 리스크로 분류됨."
            else:
                explanation_text += "로 인해 낮은 리스크로 분류됨."
            return explanation_text
        
        return f"리스크 스코어 {risk_score:.1f}점으로 {risk_level} 리스크로 분류됨."
    
    def _create_summary(
        self,
        transactions: List[Dict[str, Any]],
        time_range: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        total_volume = sum(tx.get("amount_usd", 0.0) for tx in transactions)
        
        summary = {
            "total_transactions": len(transactions),
            "total_volume_usd": total_volume
        }
        
        if time_range:
            summary["time_range"] = time_range
        
        return summary
    
    def _empty_result(self, address: str, chain: str) -> AddressAnalysisResult:
        return AddressAnalysisResult(
            address=address,
            chain=chain,
            risk_score=0.0,
            risk_level="low",
            analysis_summary={
                "total_transactions": 0,
                "total_volume_usd": 0.0
            },
            fired_rules=[],
            risk_tags=[],
            transaction_patterns={}
        )

