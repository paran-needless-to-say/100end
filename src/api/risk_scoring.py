import json
from typing import Dict, Any, List, Set
from datetime import datetime
import os
from pathlib import Path

def load_sdn_list() -> Set[str]:
    try:
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent

        sdn_path = project_root / "data" / "lists" / "sdn_addresses.json"

        if sdn_path.exists():
            with open(sdn_path, 'r') as f:
                sdn_list = json.load(f)
                return {addr.lower() for addr in sdn_list}

        return set()
    except Exception as e:
        return set()

SDN_LIST = load_sdn_list()

def convert_graph_to_transactions(graph_data: Dict[str, Any], target_address: str) -> List[Dict[str, Any]]:
    transactions = []
    edges = graph_data.get('edges', [])
    
    for edge in edges:
        from_addr = edge.get('from_address', '').lower()
        to_addr = edge.get('to_address', '').lower()
        
        is_sanctioned = from_addr in SDN_LIST or to_addr in SDN_LIST
        
        tx = {
            "tx_hash": edge.get('tx_hash', ''),
            "chain_id": edge.get('chain_id', 1),
            "timestamp": convert_timestamp(edge.get('timestamp', '')),
            "block_height": edge.get('block_height', 0),
            "from": from_addr,
            "to": to_addr,
            "target_address": target_address.lower(),
            "counterparty_address": get_counterparty(edge, target_address),
            "label": infer_label(edge),
            "is_sanctioned": is_sanctioned,  # ✅ SDN 리스트 체크!
            "is_known_scam": False,  # TODO: 사기 리스트 체크 (추후 구현)
            "is_mixer": False,  # TODO: 믹서 리스트 체크 (추후 구현)
            "is_bridge": edge.get('tx_type', '') == 'bridge',
            "amount_usd": float(edge.get('usd_value', 0)),
            "asset_contract": edge.get('token_address', '0xETH')
        }
        
        if is_sanctioned:
            print(f"🚨 SDN 주소 발견! from: {from_addr[:10]}..., to: {to_addr[:10]}...")
        
        transactions.append(tx)
    
    return transactions

def convert_timestamp(timestamp: str) -> str:
    try:
        if isinstance(timestamp, str):
            timestamp = int(timestamp)
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except:
        return "2025-01-01T00:00:00Z"

def get_counterparty(edge: Dict[str, Any], target_address: str) -> str:
    from_addr = edge.get('from_address', '').lower()
    to_addr = edge.get('to_address', '').lower()
    target = target_address.lower()
    
    if from_addr == target:
        return to_addr
    else:
        return from_addr

def infer_label(edge: Dict[str, Any]) -> str:
    tx_type = edge.get('tx_type', '')
    
    if tx_type == 'bridge':
        return 'bridge'
    elif tx_type == 'swap':
        return 'dex'
    else:
        return 'unknown'

def _convert_chain_id_to_chain(chain_id: int) -> str:
    chain_id_map = {
        1: "ethereum",
        11155111: "ethereum",
        17000: "ethereum",
        42161: "arbitrum",
        42170: "arbitrum",
        421614: "arbitrum",
        43114: "avalanche",
        43113: "avalanche",
        8453: "base",
        84532: "base",
        137: "polygon",
        80001: "polygon",
        56: "bsc",
        97: "bsc",
        250: "fantom",
        10: "optimism",
        420: "optimism",
        81457: "blast",
    }
    return chain_id_map.get(chain_id, "ethereum")

def analyze_address_with_risk_scoring(
    address: str,
    chain_id: int,
    graph_data: Dict[str, Any],
    analysis_type: str = "basic"
) -> Dict[str, Any]:
    from src.risk_engine.scoring.address_analyzer import AddressAnalyzer

    transactions = convert_graph_to_transactions(graph_data, address)

    chain = _convert_chain_id_to_chain(chain_id)

    processed_transactions = []
    for tx in transactions:
        tx_chain_id = tx.get("chain_id")
        if tx_chain_id is not None:
            tx["chain"] = _convert_chain_id_to_chain(tx_chain_id)
        processed_transactions.append(tx)

    analyzer = AddressAnalyzer()
    result = analyzer.analyze_address(
        address=address,
        chain=chain,
        transactions=processed_transactions,
        time_range=None,
        analysis_type=analysis_type
    )

    chain_to_id_map = {
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
    result_chain_id = chain_to_id_map.get(chain.lower(), 1)

    latest_timestamp = ""
    total_value = 0.0
    if transactions:
        sorted_txs = sorted(
            transactions,
            key=lambda tx: tx.get("timestamp", ""),
            reverse=True
        )
        if sorted_txs:
            latest_timestamp = sorted_txs[0].get("timestamp", "")
            total_value = sum(float(tx.get("amount_usd", 0)) for tx in transactions)

    return {
        "target_address": result.address,
        "risk_score": int(result.risk_score),
        "risk_level": result.risk_level,
        "risk_tags": result.risk_tags,
        "fired_rules": result.fired_rules,
        "explanation": result.explanation,
        "completed_at": result.completed_at,
        "timestamp": latest_timestamp,
        "chain_id": result_chain_id,
        "value": float(total_value)
    }
