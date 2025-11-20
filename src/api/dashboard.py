import requests
import time
import os
from flask import jsonify, request

QUERY_ID = "6234256"
DUNE_API_KEY = os.getenv("DUNE_API_KEY")
BASE = "https://api.dune.com/api/v1/"
headers = {"x-dune-api-key": DUNE_API_KEY}

def run_query():
    exec_url = BASE + f"query/{QUERY_ID}/execute"
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

def format_usd(value):
    return f"${value:,.0f}"