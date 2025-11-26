from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.risk_engine.data.etherscan_client import RealDataCollector
from src.risk_engine.scoring.dataset_builder import DatasetBuilder
from src.risk_engine.data.lists import ListLoader

class RealDatasetBuilder:
    
    def __init__(self, api_key: Optional[str] = None, chain: str = "ethereum"):
        self.api_key = api_key or "91FZVKNIX7GYPESECU5PHPZIMKD72REX43"
        self.collector = RealDataCollector(api_key=self.api_key, chain=chain)
        self.dataset_builder = DatasetBuilder()
        self.list_loader = ListLoader()
        self.chain = chain
    
    def build_from_high_risk_addresses(
        self,
        addresses: List[str],
        max_transactions_per_address: int = 100,
        output_path: str = "data/dataset/real_high_risk.json"
    ) -> List[Dict[str, Any]]:
        print(f"고위험 주소 {len(addresses)}개에서 거래 수집 중...")
        
        transactions = self.collector.collect_high_risk_addresses(
            addresses=addresses,
            max_transactions_per_address=max_transactions_per_address
        )
        
        print(f"수집된 거래 수: {len(transactions)}")
        
        dataset = []
        
        sdn_list = self.list_loader.get_sdn_list()
        mixer_list = self.list_loader.get_mixer_list()
        
        for tx in transactions:
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            
            is_sanctioned = (
                from_addr in sdn_list or
                to_addr in sdn_list
            )
            is_mixer = (
                from_addr in mixer_list or
                to_addr in mixer_list
            )
            
            from_tags = self.collector.client.get_address_tags(from_addr)
            to_tags = self.collector.client.get_address_tags(to_addr)
            
            entity_type = "unknown"
            if is_mixer:
                entity_type = "mixer"
            elif is_sanctioned:
                entity_type = "sanctioned"
            elif to_tags.get("is_exchange") or from_tags.get("is_exchange"):
                entity_type = "cex"
            elif to_tags.get("is_token") or from_tags.get("is_token"):
                entity_type = "token"
            elif to_tags.get("is_contract") or from_tags.get("is_contract"):
                entity_type = "contract"
            
            if is_sanctioned or is_mixer:
                label = "fraud"
                score = 85.0
            elif entity_type in ["cex", "dex"]:
                label = "normal"
                score = 15.0
            else:
                label = "normal"
                score = 15.0
            
            tx["is_sanctioned"] = is_sanctioned
            tx["is_mixer"] = is_mixer
            tx["is_known_scam"] = False  # 별도 리스트 필요
            tx["is_bridge"] = False  # 별도 리스트 필요
            tx["label"] = entity_type
            tx["from_tags"] = from_tags
            tx["to_tags"] = to_tags
            
            rule_results = self.dataset_builder.rule_evaluator.evaluate_single_transaction(
                self._convert_to_rule_data(tx)
            )
            
            tx_context = {
                "amount_usd": tx.get("amount_usd", 0),
                "is_sanctioned": is_sanctioned,
                "is_mixer": is_mixer,
                "chain": self.chain,
            }
            
            dataset.append({
                "rule_results": rule_results,
                "actual_risk_score": score,
                "tx_context": tx_context,
                "ground_truth_label": label,
                "tx_hash": tx.get("tx_hash", ""),
                "chain": self.chain,
                "data_source": "etherscan_high_risk"
            })
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        print(f"데이터셋 저장 완료: {output_path}")
        print(f"  총 {len(dataset)}개 샘플")
        print(f"  Fraud: {sum(1 for d in dataset if d['ground_truth_label'] == 'fraud')}개")
        print(f"  Normal: {sum(1 for d in dataset if d['ground_truth_label'] == 'normal')}개")
        
        return dataset
    
    def build_from_known_addresses(
        self,
        high_risk_addresses: List[str],
        normal_addresses: List[str],
        max_transactions_per_address: int = 50,
        output_path: str = "data/dataset/real_balanced.json"
    ) -> List[Dict[str, Any]]:
        print(f"고위험 주소 {len(high_risk_addresses)}개 수집 중...")
        high_risk_txs = self.collector.collect_high_risk_addresses(
            addresses=high_risk_addresses,
            max_transactions_per_address=max_transactions_per_address
        )
        
        print(f"정상 주소 {len(normal_addresses)}개 수집 중...")
        normal_txs = self.collector.collect_high_risk_addresses(
            addresses=normal_addresses,
            max_transactions_per_address=max_transactions_per_address
        )
        
        dataset = []
        
        sdn_list = self.list_loader.get_sdn_list()
        mixer_list = self.list_loader.get_mixer_list()
        
        for tx in high_risk_txs:
            is_sanctioned = (
                tx.get("from", "").lower() in sdn_list or
                tx.get("to", "").lower() in sdn_list
            )
            is_mixer = (
                tx.get("from", "").lower() in mixer_list or
                tx.get("to", "").lower() in mixer_list
            )
            
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            from_tags = self.collector.client.get_address_tags(from_addr)
            to_tags = self.collector.client.get_address_tags(to_addr)
            
            entity_type = "unknown"
            if is_mixer:
                entity_type = "mixer"
            elif is_sanctioned:
                entity_type = "sanctioned"
            elif to_tags.get("is_exchange") or from_tags.get("is_exchange"):
                entity_type = "cex"
            elif to_tags.get("is_token") or from_tags.get("is_token"):
                entity_type = "token"
            elif to_tags.get("is_contract") or from_tags.get("is_contract"):
                entity_type = "contract"
            
            tx["is_sanctioned"] = is_sanctioned
            tx["is_mixer"] = is_mixer
            tx["label"] = entity_type
            tx["from_tags"] = from_tags
            tx["to_tags"] = to_tags
            
            rule_results = self.dataset_builder.rule_evaluator.evaluate_single_transaction(
                self._convert_to_rule_data(tx)
            )
            
            dataset.append({
                "rule_results": rule_results,
                "actual_risk_score": 85.0,
                "tx_context": {
                    "amount_usd": tx.get("amount_usd", 0),
                    "is_sanctioned": is_sanctioned,
                    "is_mixer": is_mixer,
                    "chain": self.chain,
                },
                "ground_truth_label": "fraud",
                "tx_hash": tx.get("tx_hash", ""),
                "chain": self.chain,
                "data_source": "etherscan_high_risk"
            })
        
        for tx in normal_txs:
            tx["is_sanctioned"] = False
            tx["is_mixer"] = False
            tx["label"] = "cex"  # 또는 "dex", "defi" 등
            
            rule_results = self.dataset_builder.rule_evaluator.evaluate_single_transaction(
                self._convert_to_rule_data(tx)
            )
            
            dataset.append({
                "rule_results": rule_results,
                "actual_risk_score": 15.0,
                "tx_context": {
                    "amount_usd": tx.get("amount_usd", 0),
                    "is_sanctioned": False,
                    "is_mixer": False,
                    "chain": self.chain,
                },
                "ground_truth_label": "normal",
                "tx_hash": tx.get("tx_hash", ""),
                "chain": self.chain,
                "data_source": "etherscan_normal"
            })
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        print(f"데이터셋 저장 완료: {output_path}")
        print(f"  총 {len(dataset)}개 샘플")
        print(f"  Fraud: {sum(1 for d in dataset if d['ground_truth_label'] == 'fraud')}개")
        print(f"  Normal: {sum(1 for d in dataset if d['ground_truth_label'] == 'normal')}개")
        
        return dataset
    
    def _convert_to_rule_data(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "from": tx.get("from", ""),
            "to": tx.get("to", ""),
            "tx_hash": tx.get("tx_hash", ""),
            "timestamp": tx.get("timestamp", ""),
            "usd_value": tx.get("amount_usd", 0.0),
            "chain": tx.get("chain", self.chain),
            "block_height": tx.get("block_height", 0),
            "is_sanctioned": tx.get("is_sanctioned", False),
            "is_known_scam": tx.get("is_known_scam", False),
            "is_mixer": tx.get("is_mixer", False),
            "is_bridge": tx.get("is_bridge", False),
            "label": tx.get("label", "unknown"),
            "asset_contract": tx.get("asset_contract", ""),
        }

if __name__ == "__main__":
    import os
    
    API_KEY = os.getenv("ETHERSCAN_API_KEY")
    if not API_KEY:
        print("Error: ETHERSCAN_API_KEY 환경변수를 설정하세요")
        exit(1)
    
    builder = RealDatasetBuilder(api_key=API_KEY, chain="ethereum")
    
    from src.risk_engine.data.lists import ListLoader
    list_loader = ListLoader()
    
    high_risk_addresses = list(list_loader.get_sdn_list())[:10]
    high_risk_addresses.extend(list(list_loader.get_mixer_list())[:10])
    
    dataset = builder.build_from_high_risk_addresses(
        addresses=high_risk_addresses,
        max_transactions_per_address=50,
        output_path="data/dataset/real_etherscan.json"
    )
    
    print(f"\n데이터셋 구축 완료: {len(dataset)}개 샘플")

