from flask import Blueprint, request, jsonify
from src.risk_engine.scoring.address_analyzer import AddressAnalyzer

bp = Blueprint("address_analysis", __name__, url_prefix="/api/analyze")

CHAIN_ID_MAP = {
    1: "ethereum",
    42161: "arbitrum",
    43114: "avalanche",
    8453: "base",
    137: "polygon",
    56: "bsc",
    250: "fantom",
    10: "optimism",
    81457: "blast",
}

CHAIN_TO_ID_MAP = {v: k for k, v in CHAIN_ID_MAP.items()}

@bp.route("/address", methods=["POST"])
def analyze_address():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        address = data.get("address")
        chain_id = data.get("chain_id")
        transactions = data.get("transactions", [])
        time_range = data.get("time_range")
        analysis_type = data.get("analysis_type", "basic")

        if not address:
            return jsonify({"error": "Missing required field: address"}), 400
        if not chain_id:
            return jsonify({"error": "Missing required field: chain_id"}), 400

        chain = CHAIN_ID_MAP.get(chain_id, "ethereum")

        analyzer = AddressAnalyzer()
        result = analyzer.analyze_address(
            address=address,
            chain=chain,
            transactions=transactions,
            time_range=time_range,
            analysis_type=analysis_type
        )

        latest_timestamp = ""
        total_value = 0.0
        if transactions:
            sorted_txs = sorted(transactions, key=lambda tx: tx.get("timestamp", ""), reverse=True)
            if sorted_txs:
                latest_timestamp = sorted_txs[0].get("timestamp", "")
                total_value = sum(float(tx.get("amount_usd", 0)) for tx in transactions)

        return jsonify({
            "target_address": result.address,
            "risk_score": int(result.risk_score),
            "risk_level": result.risk_level,
            "risk_tags": result.risk_tags,
            "fired_rules": result.fired_rules,
            "explanation": result.explanation,
            "completed_at": result.completed_at,
            "timestamp": latest_timestamp,
            "chain_id": chain_id,
            "value": float(total_value)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500
