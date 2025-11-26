from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Using simple rule-based weights.")

@dataclass
class RuleFeature:
    rule_id: str
    axis: str
    severity: str
    base_score: float
    pattern_type: str
    name: str

class RuleWeightLearner:
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai and SKLEARN_AVAILABLE
        self.model = None
        self.scaler = None
        self.rule_features = self._load_rule_features()
        
        self.rule_based_weights = self._calculate_rule_based_weights()
    
    def _load_rule_features(self) -> Dict[str, RuleFeature]:
        from ..rules.loader import RuleLoader
        rule_loader = RuleLoader()
        rules = rule_loader.get_rules()
        
        features = {}
        for rule in rules:
            rule_id = rule.get("id")
            if not rule_id:
                continue
            
            pattern_type = "single"
            if "window" in rule:
                pattern_type = "window"
            elif "bucket" in rule:
                pattern_type = "bucket"
            elif "topology" in rule:
                pattern_type = "topology"
            elif "prerequisites" in rule:
                pattern_type = "stats"
            
            score_value = rule.get("score", 0)
            if isinstance(score_value, str) and score_value.lower() == "dynamic":
                base_score = 15.0
            else:
                try:
                    base_score = float(score_value)
                except (ValueError, TypeError):
                    base_score = 0.0
            
            features[rule_id] = RuleFeature(
                rule_id=rule_id,
                axis=rule.get("axis", "B"),
                severity=rule.get("severity", "MEDIUM"),
                base_score=base_score,
                pattern_type=pattern_type,
                name=rule.get("name", rule_id)
            )
        
        return features
    
    def _calculate_rule_based_weights(self) -> Dict[str, float]:
        weights = {}
        
        for rule_id, feature in self.rule_features.items():
            weight = 1.0
            
            if feature.severity == "HIGH":
                weight *= 1.2
            elif feature.severity == "MEDIUM":
                weight *= 1.0
            elif feature.severity == "LOW":
                weight *= 0.8
            
            if feature.axis == "C":  # Compliance는 중요
                weight *= 1.1
            elif feature.axis == "E":  # Exposure도 중요
                weight *= 1.1
            elif feature.axis == "B":  # Behavior는 상대적으로 덜 중요
                weight *= 0.95
            
            if feature.pattern_type == "topology":  # 그래프 패턴은 중요
                weight *= 1.15
            elif feature.pattern_type == "window":  # 시간 패턴도 중요
                weight *= 1.05
            
            weights[rule_id] = weight
        
        return weights
    
    def extract_features(self, rule_results: List[Dict[str, Any]], tx_context: Optional[Dict[str, Any]] = None) -> np.ndarray:
        feature_vectors = []
        
        for rule in rule_results:
            rule_id = rule.get("rule_id")
            if rule_id not in self.rule_features:
                continue
            
            feature = self.rule_features[rule_id]
            
            fv = [
                1.0 if feature.axis == "C" else 0.0,
                1.0 if feature.axis == "E" else 0.0,
                1.0 if feature.axis == "B" else 0.0,
                
                1.0 if feature.severity == "HIGH" else 0.0,
                1.0 if feature.severity == "MEDIUM" else 0.0,
                1.0 if feature.severity == "LOW" else 0.0,
                
                feature.base_score / 30.0,
                
                1.0 if feature.pattern_type == "single" else 0.0,
                1.0 if feature.pattern_type == "window" else 0.0,
                1.0 if feature.pattern_type == "bucket" else 0.0,
                1.0 if feature.pattern_type == "topology" else 0.0,
                1.0 if feature.pattern_type == "stats" else 0.0,
                
                self._get_combination_features(rule_id, rule_results),
            ]
            
            feature_vectors.append(fv)
        
        if not feature_vectors:
            return np.zeros(15)
        
        return np.mean(feature_vectors, axis=0)
    
    def _get_combination_features(self, rule_id: str, all_rules: List[Dict[str, Any]]) -> float:
        other_rule_ids = [r.get("rule_id") for r in all_rules if r.get("rule_id") != rule_id]
        
        dangerous_combinations = {
            ("C-001", "E-101"): 1.0,  # 제재 + 믹서
            ("C-001", "B-201"): 0.8,  # 제재 + 레이어링
            ("E-101", "B-202"): 0.9,  # 믹서 + 순환
            ("C-003", "B-101"): 0.5,  # 고액 + Burst
        }
        
        max_combination_score = 0.0
        for (r1, r2), score in dangerous_combinations.items():
            if (rule_id == r1 and r2 in other_rule_ids) or (rule_id == r2 and r1 in other_rule_ids):
                max_combination_score = max(max_combination_score, score)
        
        return max_combination_score
    
    def train(
        self,
        training_data: List[Tuple[List[Dict[str, Any]], float, Optional[Dict[str, Any]]]]
    ) -> None:
        if not self.use_ai:
            print("AI 모델 사용 불가. 규칙 기반 가중치 사용.")
            return
        
        X = []
        y = []
        
        for rule_results, actual_score, tx_context in training_data:
            features = self.extract_features(rule_results, tx_context)
            X.append(features)
            y.append(actual_score)
        
        X = np.array(X)
        y = np.array(y)
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        models = {
            "gradient_boosting": GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            ),
            "random_forest": RandomForestClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            ),
        }
        
        best_model = None
        best_score = 0.0
        
        for name, model in models.items():
            y_train_levels = self._score_to_level(y_train)
            y_val_levels = self._score_to_level(y_val)
            
            model.fit(X_train, y_train_levels)
            score = model.score(X_val, y_val_levels)
            
            if score > best_score:
                best_score = score
                best_model = model
        
        self.model = best_model
        print(f"모델 학습 완료. 검증 정확도: {best_score:.2%}")
    
    def _score_to_level(self, scores: np.ndarray) -> np.ndarray:
        levels = []
        for score in scores:
            if score >= 80:
                levels.append(3)
            elif score >= 60:
                levels.append(2)
            elif score >= 30:
                levels.append(1)
            else:
                levels.append(0)
        return np.array(levels)
    
    def get_weights(
        self,
        rule_results: List[Dict[str, Any]],
        tx_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        if not self.use_ai or self.model is None:
            return {
                r.get("rule_id"): self.rule_based_weights.get(r.get("rule_id"), 1.0)
                for r in rule_results
            }
        
        features = self.extract_features(rule_results, tx_context)
        features_scaled = self.scaler.transform([features])
        
        predicted_level = self.model.predict(features_scaled)[0]
        
        level_weights = {0: 0.8, 1: 1.0, 2: 1.2, 3: 1.5}
        base_weight = level_weights.get(predicted_level, 1.0)
        
        weights = {}
        for rule in rule_results:
            rule_id = rule.get("rule_id")
            if rule_id not in self.rule_features:
                weights[rule_id] = 1.0
                continue
            
            feature = self.rule_features[rule_id]
            
            rule_weight = self.rule_based_weights.get(rule_id, 1.0)
            
            final_weight = rule_weight * base_weight
            
            weights[rule_id] = final_weight
        
        return weights
    
    def calculate_weighted_score(
        self,
        rule_results: List[Dict[str, Any]],
        tx_context: Optional[Dict[str, Any]] = None
    ) -> float:
        weights = self.get_weights(rule_results, tx_context)
        
        total_score = 0.0
        for rule in rule_results:
            rule_id = rule.get("rule_id")
            base_score = rule.get("score", 0)
            weight = weights.get(rule_id, 1.0)
            
            total_score += base_score * weight
        
        return min(100.0, total_score)

class ContextAwareWeightLearner(RuleWeightLearner):
    
    def extract_features(
        self,
        rule_results: List[Dict[str, Any]],
        tx_context: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        base_features = super().extract_features(rule_results, tx_context)
        
        if tx_context is None:
            return base_features
        
        context_features = [
            tx_context.get("amount_usd", 0) / 10000.0,  # 정규화된 거래액
            1.0 if tx_context.get("is_sanctioned", False) else 0.0,
            1.0 if tx_context.get("is_mixer", False) else 0.0,
            tx_context.get("address_age_days", 0) / 365.0,  # 정규화된 주소 나이
        ]
        
        return np.concatenate([base_features, context_features])

if __name__ == "__main__":
    learner = RuleWeightLearner(use_ai=False)
    
    rule_results = [
        {"rule_id": "C-001", "score": 30, "axis": "C", "severity": "HIGH"},
        {"rule_id": "E-101", "score": 25, "axis": "E", "severity": "HIGH"},
    ]
    
    weights = learner.get_weights(rule_results)
    print("룰별 가중치:", weights)
    
    weighted_score = learner.calculate_weighted_score(rule_results)
    print("가중치 적용 점수:", weighted_score)
    
    simple_score = sum(r.get("score", 0) for r in rule_results)
    print("단순 합산 점수:", simple_score)

