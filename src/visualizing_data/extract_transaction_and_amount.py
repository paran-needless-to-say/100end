import requests
import time
import os
from dotenv import load_dotenv


load_dotenv()

DUNE_API_KEY = os.getenv("DUNE_API_KEY")

BASE = "https://api.dune.com/api/v1/"
headers = {"x-dune-api-key": DUNE_API_KEY}

# -------------------------
# DUNE 실행 함수
# -------------------------
def run_query(query_id):
    exec_url = BASE + f"query/{query_id}/execute"
    resp = requests.post(exec_url, headers=headers).json()

    if "execution_id" not in resp:
        raise Exception(f"Query execution failed: {resp}")

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

# -------------------------
# 변화율 계산
# -------------------------
def calc_change_rate(today, yesterday):
    if yesterday == 0:
        return "0%"
    diff = today - yesterday
    rate = (diff / yesterday) * 100
    sign = "+" if rate >= 0 else ""
    return f"{sign}{rate:.1f}%"

# -------------------------
# DUNE Query IDs
# -------------------------
QUERY_TODAY_VOLUME = 6234199
QUERY_YESTERDAY_VOLUME = 6234203
QUERY_TODAY_TX = 6234216
QUERY_YESTERDAY_TX = 6234219

# -------------------------
#  함수로 감싸서 호출될 때만 실행되게 변경
# -------------------------
def get_total_data():
    try:
        # print("Loading Dune data (Total)...") 
        today_volume = run_query(QUERY_TODAY_VOLUME)[0]["total_eth"]
        yesterday_volume = run_query(QUERY_YESTERDAY_VOLUME)[0]["total_eth"]

        today_tx = run_query(QUERY_TODAY_TX)[0]["total_tx"]
        yesterday_tx = run_query(QUERY_YESTERDAY_TX)[0]["total_tx"]

        response = {
            "totalVolume": {
                "value": today_volume,
                "changeRate": calc_change_rate(today_volume, yesterday_volume)
            },
            "totalTransactions": {
                "value": today_tx,
                "changeRate": calc_change_rate(today_tx, yesterday_tx)
            }
        }
        return response
    except Exception as e:
        print(f"⚠️ Dune API Error (Total): {e}")
        # 에러 시 기본값 반환
        return {
            "totalVolume": {"value": 0, "changeRate": "0%"},
            "totalTransactions": {"value": 0, "changeRate": "0%"}
        }