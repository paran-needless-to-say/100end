import requests
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DUNE_API_KEY = os.getenv("DUNE_API_KEY")

BASE = "https://api.dune.com/api/v1/"
headers = {"x-dune-api-key": DUNE_API_KEY}

# -----------------------
# 공용 Dune 실행 함수
# -----------------------
def run_query(query_id):
    exec_url = BASE + f"query/{query_id}/execute"
    resp = requests.post(exec_url, headers=headers).json()

    if "execution_id" not in resp:
        raise Exception(f"Query failed: {resp}")

    execution_id = resp["execution_id"]

    while True:
        status = requests.get(
            BASE + f"execution/{execution_id}/status",
            headers=headers
        ).json()

        if status["state"] == "QUERY_STATE_COMPLETED":
            break
        elif status["state"] == "QUERY_STATE_FAILED":
            raise Exception(f"Query failed: {status}")

        time.sleep(1)

    result = requests.get(
        BASE + f"execution/{execution_id}/results",
        headers=headers
    ).json()

    return result["result"]["rows"]

# -----------------------
# 쿼리 ID
# -----------------------
QUERY_HIGH_VALUE = 6234256

# -----------------------
# JSON 포맷 변환 헬퍼
# -----------------------
def format_usd(value):
    return f"${value:,.0f}"

# -----------------------
# [수정됨] 함수로 감싸서 호출될 때만 실행되게 변경
# -----------------------
def get_high_transfers():
    try:
        rows = run_query(QUERY_HIGH_VALUE)
        result = []
        for row in rows:
            # ▼ [수정] .get()을 써서 안전하게 가져오기
            ts_val = row.get("block_time") or row.get("timestamp") # Dune 컬럼명이 block_time일 수도 있음
            
            # 날짜 포맷팅
            if ts_val:
                try:
                    # 문자열이면 파싱, 숫자면 변환
                    if isinstance(ts_val, str): 
                        ts_str = ts_val.replace('T', ' ').replace('Z', '')
                        ts_display = datetime.fromisoformat(ts_str).strftime("%b %d, %I:%M %p")
                    else:
                        ts_display = datetime.fromtimestamp(ts_val).strftime("%b %d, %I:%M %p")
                except:
                    ts_display = "-"
            else:
                ts_display = "-"

            result.append({
                "chain": row.get("chain", "Unknown"),
                "txHash": row.get("tx_hash", ""),
                "timestamp": ts_display,
                "value": format_usd(row.get("value_usd", 0))
            })
        return result
    except Exception as e:
        print(f"⚠️ Dune API Error (High Tx): {e}")
        return []