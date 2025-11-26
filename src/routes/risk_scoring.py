from flask import Blueprint, request, jsonify
from src.risk_engine.scoring.engine import TransactionScorer, TransactionInput

bp = Blueprint("risk_scoring", __name__, url_prefix="/api/score")

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

@bp.route("/transaction", methods=["POST"])
def score_transaction():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        try:
            chain_id = data.get("chain_id")
            if not chain_id:
                return jsonify({"error": "Missing required field: chain_id"}), 400

            chain = CHAIN_ID_MAP.get(chain_id, "ethereum")

            tx_input = TransactionInput(
                tx_hash=data["tx_hash"],
                chain=chain,
                timestamp=data["timestamp"],
                block_height=data["block_height"],
                target_address=data["target_address"],
                counterparty_address=data["counterparty_address"],
                label=data.get("label", "unknown"),
                is_sanctioned=data["is_sanctioned"],
                is_known_scam=data["is_known_scam"],
                is_mixer=data["is_mixer"],
                is_bridge=data["is_bridge"],
                amount_usd=float(data["amount_usd"]),
                asset_contract=data["asset_contract"]
            )
        except KeyError as e:
            return jsonify({"error": f"Missing required field: {e}"}), 400

        scorer = TransactionScorer()
        result = scorer.score_transaction(tx_input)

        return jsonify({
            "target_address": result.target_address,
            "risk_score": int(result.risk_score),
            "risk_level": result.risk_level,
            "risk_tags": result.risk_tags,
            "fired_rules": [
                {"rule_id": rule.rule_id, "score": int(rule.score)}
                for rule in result.fired_rules
            ],
            "explanation": result.explanation,
            "completed_at": result.completed_at,
            "timestamp": result.timestamp,
            "chain_id": result.chain_id,
            "value": float(result.value)
        }), 200

    except Exception as e:
        return jsonify({"error": f"Scoring failed: {str(e)}"}), 500
