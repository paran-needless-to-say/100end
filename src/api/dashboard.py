import requests
import time
import os
from flask import jsonify, request
from datetime import datetime, timedelta

QUERY_ID = "6234256"
BASE = "https://api.dune.com/api/v1/"
headers = {"x-dune-api-key": os.getenv("DUNE_API_KEY")}

LOCAL_CACHE = {
    "timestamp": None,
    "data": None
}
CACHE_TTL = 60

def is_cache_valid():
    if LOCAL_CACHE["timestamp"] is None:
        return False
    return (datetime.utcnow() - LOCAL_CACHE["timestamp"]) < timedelta(seconds=CACHE_TTL)

def fetch_dune_cached():
    url = f"{BASE}query/{QUERY_ID}/results"
    resp = requests.get(url, headers=headers).json()

    if resp.get("state") == "QUERY_STATE_COMPLETED":
        return resp["result"]["rows"]
    return None

def fetch_dune_force_execute():
    exec_url = f"{BASE}query/{QUERY_ID}/execute"
    resp = requests.post(exec_url, headers=headers).json()

    if "execution_id" not in resp:
        raise Exception(f"Execute failed: {resp}")

    execution_id = resp["execution_id"]

    for _ in range(100):
        status = requests.get(
            f"{BASE}execution/{execution_id}/status",
            headers=headers
        ).json()

        if status["state"] == "QUERY_STATE_COMPLETED":
            break
        elif status["state"] == "QUERY_STATE_FAILED":
            raise Exception(f"Query failed: {status}")

        time.sleep(0.2)

    final = requests.get(
        f"{BASE}execution/{execution_id}/results",
        headers=headers
    ).json()

    return final["result"]["rows"]

def get_dune_results():
    dune_api_key = os.getenv("DUNE_API_KEY")
    if not dune_api_key:
        print("⚠️  DUNE_API_KEY environment variable is not set. Dune API를 사용할 수 없습니다.")
        return []
    
    if is_cache_valid():
        print(f"✅ Dune API 캐시 사용 (캐시 데이터: {len(LOCAL_CACHE['data']) if LOCAL_CACHE['data'] else 0}개)")
        return LOCAL_CACHE["data"]

    try:
        print("🔄 Dune API 캐시된 결과 확인 중...")
        cached = fetch_dune_cached()
        if cached:
            print(f"✅ Dune API 캐시된 결과 사용 (데이터: {len(cached)}개)")
            LOCAL_CACHE["timestamp"] = datetime.utcnow()
            LOCAL_CACHE["data"] = cached
            return cached

        print("🔄 Dune API 쿼리 실행 중...")
        executed = fetch_dune_force_execute()
        print(f"✅ Dune API 쿼리 실행 완료 (데이터: {len(executed) if executed else 0}개)")
        LOCAL_CACHE["timestamp"] = datetime.utcnow()
        LOCAL_CACHE["data"] = executed
        return executed
    except Exception as e:
        print(f"❌ Dune API 오류: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"   상세 오류: {traceback.format_exc()}")
        return []
