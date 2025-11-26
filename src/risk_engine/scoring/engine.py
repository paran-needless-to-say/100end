from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from src.risk_engine.rules.evaluator import RuleEvaluator
from src.risk_engine.data.lists import ListLoader

@dataclass
class TransactionInput:
    tx_hash: str
    chain: str
    timestamp: str
    block_height: int
    target_address: str
    counterparty_address: str
    label: str
    is_sanctioned: bool
    is_known_scam: bool
    is_mixer: bool
    is_bridge: bool
    amount_usd: float
    asset_contract: str

@dataclass
class FiredRule:
    rule_id: str
    score: float

@dataclass
class ScoringResult:
    target_address: str
    risk_score: float
    risk_level: str
    risk_tags: List[str]
    fired_rules: List[FiredRule]
    explanation: str
    completed_at: str
    timestamp: str
    chain_id: int
    value: float

class TransactionScorer:
    
    def __init__(self, rules_path: str = "rules/tracex_rules.yaml"):
        self.rule_evaluator = RuleEvaluator(rules_path)
        self.list_loader = ListLoader()
    
    def score_transaction(self, tx_input: TransactionInput) -> ScoringResult:
        tx_data = self._convert_to_rule_data(tx_input)
        
        rule_results = self.rule_evaluator.evaluate_single_transaction(tx_data)
        
        risk_score = self._calculate_risk_score(rule_results)
        
        risk_level = self._determine_risk_level(risk_score)
        
        risk_tags = self._generate_risk_tags(rule_results, tx_input)
        
        fired_rules = [
            FiredRule(rule_id=r["rule_id"], score=r["score"])
            for r in rule_results
        ]
        
        explanation = self._generate_explanation(tx_input, rule_results, risk_level)
        
        completed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        chain_id = self._convert_chain_to_chain_id(tx_input.chain)
        
        return ScoringResult(
            target_address=tx_input.target_address,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_tags=risk_tags,
            fired_rules=fired_rules,
            explanation=explanation,
            completed_at=completed_at,
            timestamp=tx_input.timestamp,
            chain_id=chain_id,
            value=tx_input.amount_usd
        )
    
    def _convert_to_rule_data(self, tx: TransactionInput) -> Dict[str, Any]:
        sdn_list = self.list_loader.get_sdn_list()
        mixer_list = self.list_loader.get_mixer_list()
        
        return {
            "from": tx.counterparty_address,
            "to": tx.target_address,
            "tx_hash": tx.tx_hash,
            "timestamp": tx.timestamp,
            "usd_value": tx.amount_usd,
            "chain": tx.chain,
            "block_height": tx.block_height,
            "is_sanctioned": tx.is_sanctioned,
            "is_known_scam": tx.is_known_scam,
            "is_mixer": tx.is_mixer,
            "is_bridge": tx.is_bridge,
            "label": tx.label,  # 이전 entity_type
            "asset_contract": tx.asset_contract,
        }
    
    def _calculate_risk_score(self, rule_results: List[Dict[str, Any]]) -> float:
        try:
            from .ai_weight_learner import RuleWeightLearner
            if not hasattr(self, '_weight_learner'):
                self._weight_learner = RuleWeightLearner(use_ai=False)
            
            return self._weight_learner.calculate_weighted_score(rule_results)
        except (ImportError, AttributeError):
            total_score = sum(r.get("score", 0) for r in rule_results)
            return min(100.0, total_score)
    
    def _determine_risk_level(self, score: float) -> str:
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 30:
            return "medium"
        else:
            return "low"
    
    def _convert_chain_to_chain_id(self, chain: str) -> int:
        chain_mapping = {
            "ethereum": 1,
            "arbitrum": 42161,
            "avalanche": 43114,
            "base": 8453,
            "polygon": 137,
            "bsc": 56,
            "fantom": 250,
            "optimism": 10,
            "blast": 81457
        }
        chain_lower = chain.lower()
        return chain_mapping.get(chain_lower, 1)
    
    def _generate_risk_tags(
        self,
        rule_results: List[Dict[str, Any]],
        tx: TransactionInput
    ) -> List[str]:
        tags = set()
        
        from ..rules.loader import RuleLoader
        rule_loader = RuleLoader()
        rules = rule_loader.get_rules()
        rule_map = {rule.get("id"): rule.get("name", rule.get("id")) for rule in rules if rule.get("id")}
        
        for result in rule_results:
            rule_id = result.get("rule_id", "")
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
        
        return sorted(list(tags))
    
    def _generate_explanation(
        self,
        tx: TransactionInput,
        rule_results: List[Dict[str, Any]],
        risk_level: str
    ) -> str:
        if not rule_results:
            return "정상 거래 패턴으로 리스크가 낮습니다."
        
        from ..rules.loader import RuleLoader
        rule_loader = RuleLoader()
        rules = rule_loader.get_rules()
        rule_map = {rule.get("id"): rule.get("name", rule.get("id")) for rule in rules if rule.get("id")}
        
        parts = []
        
        mixer_rules = [r for r in rule_results if "E-101" in r.get("rule_id", "")]
        if mixer_rules or tx.is_mixer:
            amount_text = f"{tx.amount_usd:,.0f}USD 이상" if tx.amount_usd >= 1000 else f"{tx.amount_usd:,.0f}USD"
            parts.append(f"1-hop sanctioned mixer에서 {amount_text} 유입")
        
        sanction_rules = [r for r in rule_results if "C-001" in r.get("rule_id", "")]
        if sanction_rules or tx.is_sanctioned:
            parts.append("제재 대상과 거래")
        
        high_value_rules = [r for r in rule_results if "C-003" in r.get("rule_id", "") or "C-004" in r.get("rule_id", "")]
        if high_value_rules or tx.amount_usd >= 1000:
            parts.append(f"고액 거래 ({tx.amount_usd:,.0f}USD)")
        
        if not parts:
            parts.append("일반 거래")
        
        explanation = ", ".join(parts)
        
        if risk_level == "high" or risk_level == "critical":
            explanation += f"로 인해 세탁 자금 유입 패턴에 해당하여 {risk_level}로 분류됨."
        elif risk_level == "medium":
            explanation += f"로 인해 {risk_level} 리스크로 분류됨."
        else:
            explanation += f"로 인해 {risk_level} 리스크로 분류됨."
        
        return explanation

