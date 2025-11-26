from __future__ import annotations

import requests
import os
from datetime import datetime
from src.configs.token_map import TOKEN_ADDRESS_MAP
from src.api.risk_scoring import SDN_LIST

ALCHEMY_URL = os.getenv("ALCHEMY_API_KEY") or os.getenv("ALCHEMY_URL")

def calculate_simple_risk_score(transfer: dict) -> dict:
    score = 0
    level = "Low"
    
    from_addr = transfer.get("from", "").lower()
    to_addr = transfer.get("to", "").lower()
    
    if from_addr in SDN_LIST or to_addr in SDN_LIST:
        score = 90
        level = "High"
    else:
        try:
            value = float(transfer.get("value", 0))
            if value > 1000000:
                score = 70
                level = "High"
            elif value > 100000:
                score = 50
                level = "Medium"
            else:
                score = 10
                level = "Low"
        except:
            score = 10
            level = "Low"
    
    return {
        "score": score,
        "level": level
    }

def fetch_live_detection(token_filter: str | None, page_no: int = 1, page_size: int = 10):
    if not ALCHEMY_URL:
        print("⚠️  Warning: ALCHEMY_API_KEY environment variable is not set. Returning empty list.")
        return []

    if page_no < 1:
        page_no = 1

    max_count = page_no * page_size
    max_count_hex = hex(max_count)

    if token_filter and token_filter.upper() == "ETH":
        params_obj = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "category": ["external"],
            "withMetadata": True,
            "excludeZeroValue": True,
            "order": "desc",
            "maxCount": max_count_hex,
        }

    else:
        params_obj = {
            "fromBlock": "0x0",
            "toBlock": "latest",
            "category": ["erc20"],
            "withMetadata": True,
            "excludeZeroValue": True,
            "order": "desc",
            "maxCount": max_count_hex,
        }

        if token_filter:
            symbol = token_filter.upper()
            contract_address = TOKEN_ADDRESS_MAP.get(symbol)
            if not contract_address:
                return []
            params_obj["contractAddresses"] = [contract_address]

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "alchemy_getAssetTransfers",
        "params": [params_obj],
    }

    resp = requests.post(ALCHEMY_URL, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    transfers = data.get("result", {}).get("transfers", [])

    start = (page_no - 1) * page_size
    end = start + page_size
    transfers = transfers[start:end]
    result = []

    for t in transfers:
        ts_raw = t["metadata"]["blockTimestamp"]
        dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        ts_unix = int(dt.timestamp())

        risk_score = calculate_simple_risk_score(t)

        result.append({
            "txHash": t.get("hash"),
            "from_address": t.get("from"),
            "to_address": t.get("to"),
            "token": t.get("asset"),
            "amount": t.get("value"),
            "timestamp": ts_unix,
            "risk": risk_score
        })

    return result
