from typing import Dict, List, Any, Optional
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
import pickle
from pathlib import Path

from .stage1_scorer import Stage1Scorer

class Stage2Scorer:
    
    def __init__(
        self,
        stage1_scorer: Optional[Stage1Scorer] = None,
        model_type: str = "logistic",  # "logistic", "random_forest", "gradient_boosting"
        use_ppr_features: bool = True
    ):
        self.stage1_scorer = stage1_scorer or Stage1Scorer(rule_weight=0.9, graph_weight=0.1)
        self.model_type = model_type
        self.use_ppr_features = use_ppr_features
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def extract_features(
        self,
        stage1_result: Dict[str, Any],
        ml_features: Dict[str, Any],
        tx_context: Dict[str, Any]
    ) -> np.ndarray:
        features = []
        
        features.append(stage1_result["rule_score"])
        features.append(stage1_result["graph_score"])
        features.append(stage1_result["risk_score"])
        
        rule_results = stage1_result.get("rule_results", [])
        features.append(len(rule_results))
        
        axes = [r.get("axis", "B") for r in rule_results]
        features.append(axes.count("A"))  # 금액 관련
        features.append(axes.count("B"))  # 행동 패턴
        features.append(axes.count("C"))  # 연결성
        features.append(axes.count("D"))  # 시간 패턴
        features.append(axes.count("E"))  # 노출
        
        severities = [r.get("severity", "MEDIUM") for r in rule_results]
        features.append(severities.count("CRITICAL"))
        features.append(severities.count("HIGH"))
        features.append(severities.count("MEDIUM"))
        features.append(severities.count("LOW"))
        
        features.append(min(100, ml_features.get("fan_in_count", 0)))  # 클리핑
        features.append(min(100, ml_features.get("fan_out_count", 0)))
        features.append(min(100, ml_features.get("tx_primary_fan_in_count", 0)))
        features.append(min(100, ml_features.get("tx_primary_fan_out_count", 0)))
        features.append(min(100.0, ml_features.get("pattern_score", 0.0)))
        
        avg_value = ml_features.get("avg_transaction_value", 0.0)
        max_value = ml_features.get("max_transaction_value", 0.0)
        if avg_value > 0:
            features.append(min(20.0, np.log1p(avg_value)))
        else:
            features.append(0.0)
        if max_value > 0:
            features.append(min(20.0, np.log1p(max_value)))
        else:
            features.append(0.0)
        
        features.append(min(200, ml_features.get("graph_nodes", tx_context.get("graph_nodes", 0))))
        features.append(min(200, ml_features.get("num_transactions", tx_context.get("num_transactions", 0))))
        
        if self.use_ppr_features:
            features.append(min(1.0, ml_features.get("ppr_score", 0.0)))  # 0~1 범위
            features.append(min(1.0, ml_features.get("sdn_ppr", 0.0)))
            features.append(min(1.0, ml_features.get("mixer_ppr", 0.0)))
        else:
            features.extend([0.0, 0.0, 0.0])
        
        features.append(min(1.0, max(0.0, ml_features.get("n_theta", 0.0))))
        features.append(min(1.0, max(0.0, ml_features.get("n_omega", 0.0))))
        
        features.append(ml_features.get("fan_in_detected", 0))
        features.append(ml_features.get("fan_out_detected", 0))
        features.append(ml_features.get("gather_scatter_detected", 0))
        
        features_array = np.array(features, dtype=np.float32)
        features_array = np.nan_to_num(features_array, nan=0.0, posinf=100.0, neginf=0.0)
        return features_array
    
    def train(
        self,
        train_data: List[Dict[str, Any]],
        val_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        print("=" * 80)
        print("2단계 스코어러 학습")
        print("=" * 80)
        
        X_train = []
        y_train = []
        
        print("\n📊 Feature 추출 중...")
        for sample in train_data:
            label = sample.get("ground_truth_label", "normal")
            y_train.append(1 if label == "fraud" else 0)
            
            tx_data = {
                "from": sample.get("from", ""),
                "to": sample.get("to", ""),
                "usd_value": sample.get("usd_value", 0),
                "timestamp": sample.get("timestamp", 0),
                "tx_hash": sample.get("tx_hash", ""),
                "chain": sample.get("chain", "ethereum"),
                "is_sanctioned": sample.get("tx_context", {}).get("is_sanctioned", False),
                "is_mixer": sample.get("tx_context", {}).get("is_mixer", False),
            }
            
            ml_features = sample.get("ml_features", {})
            tx_context = sample.get("tx_context", {})
            
            try:
                stage1_result = self.stage1_scorer.calculate_risk_score(tx_data, ml_features, tx_context)
                features = self.extract_features(stage1_result, ml_features, tx_context)
                X_train.append(features)
            except Exception as e:
                X_train.append(np.zeros(30, dtype=np.float32))
        
        X_train = np.array(X_train)
        y_train = np.array(y_train)
        
        print(f"   학습 샘플: {len(X_train)}개")
        print(f"   Feature 차원: {X_train.shape[1]}")
        print(f"   Fraud 비율: {y_train.sum() / len(y_train) * 100:.1f}%")
        
        print("\n🔧 Feature 스케일링 중...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        print(f"\n🤖 {self.model_type} 모델 학습 중...")
        if self.model_type == "logistic":
            self.model = LogisticRegression(
                random_state=42,
                solver='liblinear',
                class_weight='balanced',
                max_iter=1000
            )
        elif self.model_type == "random_forest":
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
        elif self.model_type == "gradient_boosting":
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
        
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        
        train_accuracy = self.model.score(X_train_scaled, y_train)
        print(f"   학습 Accuracy: {train_accuracy:.4f}")
        
        results = {
            "train_accuracy": train_accuracy,
            "model_type": self.model_type,
            "feature_dim": X_train.shape[1]
        }
        
        if val_data:
            val_results = self.evaluate(val_data)
            results["val_accuracy"] = val_results.get("accuracy", 0.0)
            results["val_f1"] = val_results.get("f1_score", 0.0)
            print(f"   검증 Accuracy: {results['val_accuracy']:.4f}")
            print(f"   검증 F1-Score: {results['val_f1']:.4f}")
        
        return results
    
    def calculate_risk_score(
        self,
        tx_data: Dict[str, Any],
        ml_features: Optional[Dict[str, Any]] = None,
        tx_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        stage1_result = self.stage1_scorer.calculate_risk_score(tx_data, ml_features, tx_context)
        stage1_score = stage1_result["risk_score"]
        
        if not self.is_trained:
            return {
                "risk_score": stage1_score,
                "stage1_score": stage1_score,
                "ml_score": 0.0,
                "explanation": "2단계 모델이 학습되지 않음. 1단계 점수만 사용."
            }
        
        features = self.extract_features(stage1_result, ml_features or {}, tx_context or {})
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        ml_proba = self.model.predict_proba(features_scaled)[0]
        ml_score = ml_proba[1] * 100.0
        
        final_score = 0.6 * stage1_score + 0.4 * ml_score
        final_score = min(100.0, max(0.0, final_score))
        
        explanation = f"1단계: {stage1_score:.1f}점, ML: {ml_score:.1f}점 → 최종: {final_score:.1f}점"
        
        return {
            "risk_score": final_score,
            "stage1_score": stage1_score,
            "ml_score": ml_score,
            "explanation": explanation
        }
    
    def evaluate(
        self,
        test_data: List[Dict[str, Any]],
        threshold: float = 50.0
    ) -> Dict[str, Any]:
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score,
            roc_auc_score, average_precision_score, confusion_matrix
        )
        
        y_true = []
        y_pred = []
        y_pred_scores = []
        
        for sample in test_data:
            label = sample.get("ground_truth_label", "normal")
            y_true.append(1 if label == "fraud" else 0)
            
            tx_data = {
                "from": sample.get("from", ""),
                "to": sample.get("to", ""),
                "usd_value": sample.get("usd_value", 0),
                "timestamp": sample.get("timestamp", 0),
                "tx_hash": sample.get("tx_hash", ""),
                "chain": sample.get("chain", "ethereum"),
                "is_sanctioned": sample.get("tx_context", {}).get("is_sanctioned", False),
                "is_mixer": sample.get("tx_context", {}).get("is_mixer", False),
            }
            
            ml_features = sample.get("ml_features", {})
            tx_context = sample.get("tx_context", {})
            
            try:
                result = self.calculate_risk_score(tx_data, ml_features, tx_context)
                risk_score = result["risk_score"]
                y_pred_scores.append(risk_score)
                y_pred.append(1 if risk_score >= threshold else 0)
            except Exception as e:
                y_pred_scores.append(0.0)
                y_pred.append(0)
        
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        y_pred_proba = [s / 100.0 for s in y_pred_scores]
        roc_auc = 0.5
        avg_precision = 0.0
        if len(set(y_true)) > 1 and len(set(y_pred_proba)) > 1:
            try:
                roc_auc = roc_auc_score(y_true, y_pred_proba)
                avg_precision = average_precision_score(y_true, y_pred_proba)
            except ValueError:
                pass
        
        cm = confusion_matrix(y_true, y_pred)
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "roc_auc": roc_auc,
            "average_precision": avg_precision,
            "confusion_matrix": {
                "true_negative": int(cm[0][0]),
                "false_positive": int(cm[0][1]),
                "false_negative": int(cm[1][0]),
                "true_positive": int(cm[1][1])
            }
        }
    
    def save_model(self, model_path: Path):
        model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(model_path, 'wb') as f:
            pickle.dump({
                "model": self.model,
                "scaler": self.scaler,
                "model_type": self.model_type,
                "use_ppr_features": self.use_ppr_features
            }, f)
    
    def load_model(self, model_path: Path):
        with open(model_path, 'rb') as f:
            data = pickle.load(f)
            self.model = data["model"]
            self.scaler = data["scaler"]
            self.model_type = data["model_type"]
            self.use_ppr_features = data["use_ppr_features"]
            self.is_trained = True

