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
    if is_cache_valid():
        return LOCAL_CACHE["data"]

    cached = fetch_dune_cached()
    if cached:
        LOCAL_CACHE["timestamp"] = datetime.utcnow()
        LOCAL_CACHE["data"] = cached
        return cached

    executed = fetch_dune_force_execute()
    LOCAL_CACHE["timestamp"] = datetime.utcnow()
    LOCAL_CACHE["data"] = executed
    return executed
