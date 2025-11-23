#!/usr/bin/env python3
"""
리스크 스코어링 API 호출 테스트 스크립트
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.api.risk_scoring import RISK_SCORING_API_URL, call_risk_scoring_api

def test_risk_scoring_api():
    """리스크 스코어링 API 호출 테스트"""
    
    print("=" * 60)
    print("리스크 스코어링 API 호출 테스트")
    print("=" * 60)
    
    # 1. 환경 변수 확인
    print(f"\n1. 환경 변수 확인:")
    env_url = os.getenv("RISK_SCORING_API_URL")
    print(f"   RISK_SCORING_API_URL (환경 변수): {env_url}")
    print(f"   RISK_SCORING_API_URL (코드에서 읽은 값): {RISK_SCORING_API_URL}")
    
    # 2. URL 구성 확인
    print(f"\n2. 호출 URL 구성:")
    test_url = f"{RISK_SCORING_API_URL}/api/analyze/address"
    print(f"   전체 URL: {test_url}")
    
    # 3. Health check 테스트
    print(f"\n3. Health Check 테스트:")
    import requests
    health_url = f"{RISK_SCORING_API_URL}/health"
    try:
        response = requests.get(health_url, timeout=5)
        print(f"   Health Check URL: {health_url}")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json()}")
        print("   ✅ Health Check 성공!")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ 연결 실패: {e}")
        print(f"   ⚠️  리스크 스코어링 API가 실행 중인지 확인하세요.")
        return False
    except Exception as e:
        print(f"   ❌ 에러: {e}")
        return False
    
    # 4. 실제 API 호출 테스트 (간단한 거래 데이터)
    print(f"\n4. 실제 API 호출 테스트:")
    test_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"  # Binance Hot Wallet
    test_transactions = [
        {
            "tx_hash": "0xtest123",
            "chain_id": 1,
            "timestamp": "2025-01-15T10:00:00Z",
            "block_height": 21039493,
            "target_address": test_address.lower(),
            "counterparty_address": "0xtest456",
            "label": "cex",
            "is_sanctioned": False,
            "is_known_scam": False,
            "is_mixer": False,
            "is_bridge": False,
            "amount_usd": 100.0,
            "asset_contract": "0xETH"
        }
    ]
    
    try:
        print(f"   주소: {test_address}")
        print(f"   거래 수: {len(test_transactions)}")
        result = call_risk_scoring_api(
            address=test_address,
            chain_id=1,
            transactions=test_transactions,
            analysis_type="basic"
        )
        print(f"   ✅ API 호출 성공!")
        print(f"   Risk Score: {result.get('risk_score', 'N/A')}")
        print(f"   Risk Level: {result.get('risk_level', 'N/A')}")
        return True
    except Exception as e:
        print(f"   ❌ API 호출 실패: {e}")
        return False

if __name__ == "__main__":
    success = test_risk_scoring_api()
    print("\n" + "=" * 60)
    if success:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    print("=" * 60)
    sys.exit(0 if success else 1)

