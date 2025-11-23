"""
리스크 스코어링 API 연동 모듈

백엔드에서 거래 데이터를 수집하고 리스크 스코어링 API에 전달
"""
import requests
import json
from typing import Dict, Any, List, Set
from datetime import datetime
import os


# 리스크 스코어링 API URL
# 환경 변수에서 가져오거나 기본값 사용
# EC2 서버 외부 접근 (기본값): http://3.38.112.25:5001
# Docker Compose 내부: http://risk-scoring:5001
# 로컬 개발: http://localhost:5001
RISK_SCORING_API_URL = os.getenv("RISK_SCORING_API_URL", "http://3.38.112.25:5001")

# SDN 리스트 로드
def load_sdn_list() -> Set[str]:
    """SDN 리스트 로드"""
    try:
        # 절대 경로로 SDN 리스트 찾기
        # 현재 파일의 위치에서 상대 경로로 계산
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        
        possible_paths = [
            # 현재 프로젝트 내부 (risk-scoring)
            os.path.join(project_root, "risk-scoring/data/lists/sdn_addresses.json"),
            # 절대 경로
            "/Users/yelim/Desktop/paran_final/trace-x/risk-scoring/data/lists/sdn_addresses.json",
            # 레거시 경로 (호환성)
            "/Users/yelim/Desktop/파란학기/trace-x/data/lists/sdn_addresses.json",
        ]
        
        for sdn_path in possible_paths:
            if os.path.exists(sdn_path):
                print(f"📂 SDN 리스트 경로: {sdn_path}")
                with open(sdn_path, 'r') as f:
                    sdn_list = json.load(f)
                    # 소문자로 변환하여 Set에 저장
                    return {addr.lower() for addr in sdn_list}
        
        # 파일을 찾지 못한 경우
        print(f"❌ SDN 리스트를 찾을 수 없습니다. 확인한 경로: {possible_paths}")
        return set()
    except Exception as e:
        print(f"Warning: Failed to load SDN list: {e}")
        return set()

# SDN 리스트 캐시 (앱 시작 시 한 번만 로드)
SDN_LIST = load_sdn_list()
print(f"✅ SDN 리스트 로드 완료: {len(SDN_LIST)}개 주소")


def convert_graph_to_transactions(graph_data: Dict[str, Any], target_address: str) -> List[Dict[str, Any]]:
    """
    백엔드의 그래프 데이터를 리스크 스코어링 API 형식으로 변환
    
    Args:
        graph_data: 백엔드 그래프 데이터 (nodes, edges)
        target_address: 분석 대상 주소
    
    Returns:
        리스크 스코어링 API 형식의 거래 배열
    """
    transactions = []
    edges = graph_data.get('edges', [])
    
    for edge in edges:
        # 거래 데이터 변환
        from_addr = edge.get('from_address', '').lower()
        to_addr = edge.get('to_address', '').lower()
        
        # SDN 리스트 체크: from 또는 to가 SDN 리스트에 있는지 확인
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
        
        # 디버깅: SDN 주소 발견 시 로그
        if is_sanctioned:
            print(f"🚨 SDN 주소 발견! from: {from_addr[:10]}..., to: {to_addr[:10]}...")
        
        transactions.append(tx)
    
    return transactions


def convert_timestamp(timestamp: str) -> str:
    """
    Unix timestamp를 ISO8601 형식으로 변환
    
    Args:
        timestamp: Unix timestamp (문자열 또는 숫자)
    
    Returns:
        ISO8601 UTC 형식 문자열
    """
    try:
        if isinstance(timestamp, str):
            timestamp = int(timestamp)
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except:
        return "2025-01-01T00:00:00Z"


def get_counterparty(edge: Dict[str, Any], target_address: str) -> str:
    """
    상대방 주소 추출
    
    Args:
        edge: 거래 edge 데이터
        target_address: 분석 대상 주소
    
    Returns:
        counterparty 주소
    """
    from_addr = edge.get('from_address', '').lower()
    to_addr = edge.get('to_address', '').lower()
    target = target_address.lower()
    
    if from_addr == target:
        return to_addr
    else:
        return from_addr


def infer_label(edge: Dict[str, Any]) -> str:
    """
    거래 타입에서 라벨 추론
    
    Args:
        edge: 거래 edge 데이터
    
    Returns:
        "mixer" | "bridge" | "cex" | "dex" | "defi" | "unknown"
    """
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
    """
    리스크 스코어링 API 호출
    
    Args:
        address: 분석 대상 주소
        chain_id: 체인 ID
        transactions: 거래 배열
        analysis_type: "basic" 또는 "advanced"
    
    Returns:
        리스크 스코어링 결과
    """
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
    """
    주소 분석 + 리스크 스코어링
    
    Args:
        address: 분석 대상 주소
        chain_id: 체인 ID
        graph_data: 백엔드 그래프 데이터
        analysis_type: "basic" 또는 "advanced"
    
    Returns:
        리스크 스코어링 결과
    """
    # 1. 그래프 데이터를 거래 배열로 변환
    transactions = convert_graph_to_transactions(graph_data, address)
    
    # 2. 리스크 스코어링 API 호출
    result = call_risk_scoring_api(address, chain_id, transactions, analysis_type)
    
    return result

