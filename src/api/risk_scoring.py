import requests
import json
from typing import Dict, Any, List, Set
from datetime import datetime
import os

RISK_SCORING_API_URL = os.getenv("RISK_SCORING_API_URL", "http://3.38.112.25:5001")

def load_sdn_list() -> Set[str]:
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        
        possible_paths = [
            os.path.join(project_root, "risk-scoring/data/lists/sdn_addresses.json"),
            "/Users/yelim/Desktop/paran_final/trace-x/risk-scoring/data/lists/sdn_addresses.json",
            "/Users/yelim/Desktop/파란학기/trace-x/data/lists/sdn_addresses.json",
        ]
        
        for sdn_path in possible_paths:
            if os.path.exists(sdn_path):
                print(f"📂 SDN 리스트 경로: {sdn_path}")
                with open(sdn_path, 'r') as f:
                    sdn_list = json.load(f)
                    return {addr.lower() for addr in sdn_list}
        
        print(f"❌ SDN 리스트를 찾을 수 없습니다. 확인한 경로: {possible_paths}")
        return set()
    except Exception as e:
        print(f"Warning: Failed to load SDN list: {e}")
        return set()

SDN_LIST = load_sdn_list()
print(f"✅ SDN 리스트 로드 완료: {len(SDN_LIST)}개 주소")

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

def call_risk_scoring_api(
    address: str,
    chain_id: int,
    transactions: List[Dict[str, Any]],
    analysis_type: str = "basic"
) -> Dict[str, Any]:
    url = f"{RISK_SCORING_API_URL}/api/analyze/address"
    
    payload = {
        "address": address,
        "chain_id": chain_id,
        "transactions": transactions,
        "analysis_type": analysis_type
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Risk scoring API call failed: {str(e)}")

def analyze_address_with_risk_scoring(
    address: str,
    chain_id: int,
    graph_data: Dict[str, Any],
    analysis_type: str = "basic"
) -> Dict[str, Any]:
    transactions = convert_graph_to_transactions(graph_data, address)
    
    result = call_risk_scoring_api(address, chain_id, transactions, analysis_type)
    
    return result
