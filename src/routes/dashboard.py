from datetime import datetime
from flask import Blueprint, jsonify, current_app
from src.api.live_detection import fetch_live_detection

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@bp.route('/summary', methods=['GET'])
def get_summary():
    return jsonify({
        'data': {
            'totalVolume': {'value': 0, 'changeRate': '0'},
            'totalTransactions': {'value': 0, 'changeRate': '0'},
            'highRiskTransactions': {'value': 0, 'changeRate': '0'},
            'warningTransactions': {'value': 0, 'changeRate': '0'},
            'highRiskTransactionTrend': {},
            'highRiskTransactionsByChain': {},
            'averageRiskScore': {}
        }
    }), 200

@bp.route('/monitoring', methods=['GET'])
def get_monitoring():
    try:
        from src.api.dashboard import get_dune_results
        rows = get_dune_results()

        if rows and len(rows) > 0:
            formatted = []
            for row in rows:
                formatted.append({
                    "chain": row.get("chain", ""),
                    "txHash": row.get("tx_hash", ""),
                    "timestamp": datetime.fromtimestamp(row.get("display_timestamp", 0)).strftime("%b %d, %I:%M %p"),
                    "value": f"${row.get('value_usd', 0):,.2f}"
                })

            return jsonify({
                "RecentHighValueTransfers": formatted,
            }), 200

        print("⚠️  Dune API 결과 없음, Alchemy API로 fallback...")

        results = fetch_live_detection(
            token_filter=None,
            page_no=1,
            page_size=3
        )

        if not results or len(results) == 0:
            print("⚠️  Alchemy API도 데이터를 반환하지 않았습니다.")
            return jsonify({
                "RecentHighValueTransfers": [],
            }), 200

        print(f"✅ Alchemy API fallback 성공 (데이터: {len(results)}개)")

        formatted = _format_alchemy_results(results)

        return jsonify({
            "RecentHighValueTransfers": formatted,
        }), 200

    except Exception as e:
        print(f"❌ Alchemy API fallback 오류: {e}")
        return jsonify({
            "RecentHighValueTransfers": [],
        }), 200

def _format_alchemy_results(results):
    formatted = []
    token_prices = {
        "ETH": 3000.0,
        "USDT": 1.0,
        "USDC": 1.0,
        "DAI": 1.0,
    }

    for transfer in results:
        try:
            dt = datetime.fromtimestamp(transfer["timestamp"])
            formatted_timestamp = dt.strftime("%b %d, %I:%M %p")

            amount = float(transfer.get("amount", 0))
            token = transfer.get("token", "")

            price = token_prices.get(token.upper(), 1.0)
            if not token or token.startswith("0x"):
                price = 1.0

            usd_value = amount * price

            if usd_value >= 1.0:
                formatted.append({
                    "chain": "ethereum",
                    "txHash": transfer.get("txHash", ""),
                    "timestamp": formatted_timestamp,
                    "value": f"${usd_value:,.2f}"
                })
        except Exception as e:
            print(f"⚠️ Error formatting transfer: {e}")
            continue

    return formatted[:3]
