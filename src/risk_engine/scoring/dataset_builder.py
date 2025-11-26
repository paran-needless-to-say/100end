from __future__ import annotations

import json
import csv
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import random

from src.risk_engine.scoring.engine import TransactionScorer, TransactionInput
from src.risk_engine.scoring.address_analyzer import AddressAnalyzer
from src.risk_engine.rules.evaluator import RuleEvaluator

class DatasetBuilder:
    
    def __init__(self):
        self.scorer = TransactionScorer()
        self.analyzer = AddressAnalyzer()
        self.rule_evaluator = RuleEvaluator()
    
    def build_from_legacy_features(
        self,
        features_path: str,
        transactions_dir: str,
        output_path: str
    ) -> List[Dict[str, Any]]:
        df = pd.read_csv(features_path)
        
        dataset = []
        
        for _, row in df.iterrows():
            chain = row['Chain'].lower()
            contract = row['Contract']
            label = int(row.get('label', 0))  # 0: normal, 1: fraud
            
            tx_file = Path(transactions_dir) / chain / f"{contract}.csv"
            if not tx_file.exists():
                continue
            
            transactions = self._load_transactions_from_csv(tx_file, chain, contract)
            
            if not transactions:
                continue
            
            for tx in transactions:
                rule_results = self.rule_evaluator.evaluate_single_transaction(tx)
                
                actual_score = self._label_to_score(label)
                
                tx_context = {
                    "amount_usd": tx.get("usd_value", tx.get("amount_usd", 0)),
                    "is_sanctioned": tx.get("is_sanctioned", False),
                    "is_mixer": tx.get("is_mixer", False),
                    "chain": chain,
                }
                
                dataset.append({
                    "rule_results": rule_results,
                    "actual_risk_score": actual_score,
                    "tx_context": tx_context,
                    "ground_truth_label": "fraud" if label == 1 else "normal",
                    "tx_hash": tx.get("tx_hash", ""),
                    "chain": chain,
                    "contract": contract
                })
        
        with open(output_path, 'w') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        print(f"데이터셋 구축 완료: {len(dataset)}개 샘플")
        return dataset
    
    def build_from_demo_scenarios(
        self,
        demo_dir: str = "demo/transactions",
        output_path: str = "data/dataset/demo_labeled.json"
    ) -> List[Dict[str, Any]]:
        demo_path = Path(demo_dir)
        dataset = []
        
        scenario_labels = {
            "high_risk": {"label": "fraud", "score": 85.0},
            "medium_risk": {"label": "suspicious", "score": 60.0},
            "low_risk": {"label": "normal", "score": 15.0},
        }
        
        for tx_file in demo_path.glob("*.json"):
            scenario_type = None
            for key in scenario_labels.keys():
                if key in tx_file.stem:
                    scenario_type = key
                    break
            
            if not scenario_type:
                continue
            
            label_info = scenario_labels[scenario_type]
            
            with open(tx_file, 'r') as f:
                transactions = json.load(f)
            
            for tx in transactions:
                tx_data = self._convert_demo_tx(tx)
                
                rule_results = self.rule_evaluator.evaluate_single_transaction(tx_data)
                
                tx_context = {
                    "amount_usd": tx.get("amount_usd", 0),
                    "is_sanctioned": tx.get("is_sanctioned", False),
                    "is_mixer": tx.get("is_mixer", False),
                    "chain": tx.get("chain", "ethereum"),
                }
                
                dataset.append({
                    "rule_results": rule_results,
                    "actual_risk_score": label_info["score"],
                    "tx_context": tx_context,
                    "ground_truth_label": label_info["label"],
                    "tx_hash": tx.get("tx_hash", ""),
                    "chain": tx.get("chain", "ethereum"),
                    "scenario": scenario_type
                })
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        print(f"Demo 데이터셋 구축 완료: {len(dataset)}개 샘플")
        return dataset
    
    def build_from_rule_based_labeling(
        self,
        transactions: List[Dict[str, Any]],
        output_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        dataset = []
        
        for tx in transactions:
            tx_data = self._convert_transaction(tx)
            
            rule_results = self.rule_evaluator.evaluate_single_transaction(tx_data)
            
            rule_based_score = sum(r.get("score", 0) for r in rule_results)
            rule_based_score = min(100.0, rule_based_score)
            
            if rule_based_score >= 60:
                label = "fraud"
            elif rule_based_score >= 30:
                label = "suspicious"
            else:
                label = "normal"
            
            tx_context = {
                "amount_usd": tx.get("amount_usd", tx.get("usd_value", 0)),
                "is_sanctioned": tx.get("is_sanctioned", False),
                "is_mixer": tx.get("is_mixer", False),
                "chain": tx.get("chain", "ethereum"),
            }
            
            dataset.append({
                "rule_results": rule_results,
                "actual_risk_score": rule_based_score,  # 규칙 기반 점수를 라벨로 사용
                "tx_context": tx_context,
                "ground_truth_label": label,
                "tx_hash": tx.get("tx_hash", ""),
                "chain": tx.get("chain", "ethereum"),
                "labeling_method": "rule_based"
            })
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        return dataset
    
    def split_dataset(
        self,
        dataset: List[Dict[str, Any]],
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        stratify: bool = True
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        if stratify:
            fraud_data = [d for d in dataset if d.get("ground_truth_label") == "fraud"]
            suspicious_data = [d for d in dataset if d.get("ground_truth_label") == "suspicious"]
            normal_data = [d for d in dataset if d.get("ground_truth_label") == "normal"]
            
            def split_list(lst, train_r, val_r):
                random.shuffle(lst)
                n = len(lst)
                train_end = int(n * train_r)
                val_end = train_end + int(n * val_r)
                return lst[:train_end], lst[train_end:val_end], lst[val_end:]
            
            train_fraud, val_fraud, test_fraud = split_list(fraud_data, train_ratio, val_ratio)
            train_susp, val_susp, test_susp = split_list(suspicious_data, train_ratio, val_ratio)
            train_normal, val_normal, test_normal = split_list(normal_data, train_ratio, val_ratio)
            
            train_dataset = train_fraud + train_susp + train_normal
            val_dataset = val_fraud + val_susp + val_normal
            test_dataset = test_fraud + test_susp + test_normal
            
            random.shuffle(train_dataset)
            random.shuffle(val_dataset)
            random.shuffle(test_dataset)
        else:
            random.shuffle(dataset)
            n = len(dataset)
            train_end = int(n * train_ratio)
            val_end = train_end + int(n * val_ratio)
            
            train_dataset = dataset[:train_end]
            val_dataset = dataset[train_end:val_end]
            test_dataset = dataset[val_end:]
        
        return train_dataset, val_dataset, test_dataset
    
    def _load_transactions_from_csv(
        self,
        csv_path: Path,
        chain: str,
        contract: str
    ) -> List[Dict[str, Any]]:
        transactions = []
        
        try:
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                tx = {
                    "tx_hash": row.get("transaction_hash", ""),
                    "from": row.get("from", ""),
                    "to": row.get("to", ""),
                    "timestamp": row.get("timestamp", 0),
                    "usd_value": 0.0,  # USD 변환 필요
                    "chain": chain,
                    "asset_contract": contract,
                }
                transactions.append(tx)
        except Exception as e:
            print(f"Error loading {csv_path}: {e}")
        
        return transactions
    
    def _convert_demo_tx(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "from": tx.get("from") or tx.get("counterparty_address", ""),
            "to": tx.get("to") or tx.get("target_address", ""),
            "tx_hash": tx.get("tx_hash", ""),
            "timestamp": tx.get("timestamp", ""),
            "usd_value": tx.get("amount_usd", 0.0),
            "chain": tx.get("chain", "ethereum"),
            "block_height": tx.get("block_height", 0),
            "is_sanctioned": tx.get("is_sanctioned", False),
            "is_known_scam": tx.get("is_known_scam", False),
            "is_mixer": tx.get("is_mixer", False),
            "is_bridge": tx.get("is_bridge", False),
            "label": tx.get("label", "unknown"),
            "asset_contract": tx.get("asset_contract", ""),
        }
    
    def _convert_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "from": tx.get("from") or tx.get("counterparty_address", ""),
            "to": tx.get("to") or tx.get("target_address", ""),
            "tx_hash": tx.get("tx_hash", ""),
            "timestamp": tx.get("timestamp", ""),
            "usd_value": tx.get("amount_usd", tx.get("usd_value", 0.0)),
            "chain": tx.get("chain", "ethereum"),
            "block_height": tx.get("block_height", 0),
            "is_sanctioned": tx.get("is_sanctioned", False),
            "is_known_scam": tx.get("is_known_scam", False),
            "is_mixer": tx.get("is_mixer", False),
            "is_bridge": tx.get("is_bridge", False),
            "label": tx.get("label", "unknown"),
            "asset_contract": tx.get("asset_contract", ""),
        }
    
    def _label_to_score(self, label: int) -> float:
        if label == 1:
            return 85.0
        else:
            return 15.0

class ExpertLabelingTool:
    
    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self.labeled_path = self.dataset_path.parent / f"{self.dataset_path.stem}_labeled.json"
    
    def create_labeling_template(self, output_path: str) -> None:
        with open(self.dataset_path, 'r') as f:
            dataset = json.load(f)
        
        template = []
        for i, item in enumerate(dataset):
            template.append({
                "id": i,
                "tx_hash": item.get("tx_hash", ""),
                "rule_results": item.get("rule_results", []),
                "rule_based_score": sum(r.get("score", 0) for r in item.get("rule_results", [])),
                "expert_label": None,  # 전문가가 채울 필드
                "expert_score": None,  # 전문가가 채울 필드 (0~100)
                "notes": ""  # 메모
            })
        
        with open(output_path, 'w') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        print(f"라벨링 템플릿 생성: {output_path}")
        print(f"총 {len(template)}개 샘플")
    
    def load_labeled_data(self, labeled_path: str) -> List[Dict[str, Any]]:
        with open(labeled_path, 'r') as f:
            labeled = json.load(f)
        
        with open(self.dataset_path, 'r') as f:
            original = json.load(f)
        
        labeled_dict = {item["id"]: item for item in labeled}
        
        merged = []
        for i, item in enumerate(original):
            if i in labeled_dict:
                label_info = labeled_dict[i]
                item["actual_risk_score"] = label_info.get("expert_score", item.get("actual_risk_score", 0))
                item["ground_truth_label"] = self._score_to_label(label_info.get("expert_score", 0))
                item["labeling_method"] = "expert"
                item["expert_notes"] = label_info.get("notes", "")
            
            merged.append(item)
        
        return merged
    
    def _score_to_label(self, score: float) -> str:
        if score >= 60:
            return "fraud"
        elif score >= 30:
            return "suspicious"
        else:
            return "normal"

if __name__ == "__main__":
    builder = DatasetBuilder()
    
    demo_dataset = builder.build_from_demo_scenarios(
        demo_dir="demo/transactions",
        output_path="data/dataset/demo_labeled.json"
    )
    
    
    
    train, val, test = builder.split_dataset(demo_dataset)
    
    print(f"학습: {len(train)}개, 검증: {len(val)}개, 테스트: {len(test)}개")

