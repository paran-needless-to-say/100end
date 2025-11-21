from datetime import datetime

from flask import Flask, jsonify, request, current_app
from flask_cors import CORS
from src.api.analysis import Analyzer
from src.api.live_detection import fetch_live_detection
from src.api.dashboard import get_dune_results, LOCAL_CACHE
from src.constants.rpc_urls import URLS as RPC_URLS


def create_app(api_key: str) -> Flask:
    app = Flask(__name__)
    # CORS(app, origins=["http://localhost:5173", "https://trace-x-two.vercel.app/"])
    CORS(app)
    app.analyzer = Analyzer(api_key=api_key)

    @app.route('/api/dashboard/summary', methods=['GET'])
    def get_dashboard_summary():
        return jsonify({'message': 'Not implemented'}), 501

    @app.route('/api/dashboard/monitoring', methods=['GET'])
    def get_dashboard_monitoring():
        try:
            rows = get_dune_results()

            formatted = []
            for row in rows:
                formatted.append({
                    "chain": row["chain"],
                    "txHash": row["tx_hash"],
                    "timestamp": datetime.fromtimestamp(row["display_timestamp"]).strftime("%b %d, %I:%M %p"),
                    "value": f"${row['value_usd']:,.0f}"
                })

            return jsonify({
                "RecentHighValueTransfers": formatted,
                "cache_age_seconds": (datetime.utcnow() - LOCAL_CACHE["timestamp"]).total_seconds()
            }), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/live-detection/summary', methods=['GET'])
    def get_live_detection_summary():
        token_filter = request.args.get("tokenFilter")
        page_no = request.args.get("pageNo", "1")

        try:
            page_no_int = int(page_no)
        except:
            page_no_int = 1

        try:
            results = fetch_live_detection(
                token_filter=token_filter,
                page_no=page_no_int,
                page_size=10
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        return jsonify({"data": results}), 200

    @app.route('/api/analysis/fund-flow', methods=['GET'])
    def get_fund_flow_analysis():
        chain_id = request.args.get('chain_id')
        address = request.args.get('address')

        if not chain_id:
            return jsonify({'error': 'chain_id is required'}), 400

        if not address:
            return jsonify({'error': 'address is required'}), 400

        try:
            chain_id = int(chain_id)
        except ValueError:
            return jsonify({'error': 'chain_id must be a valid integer'}), 400

        if str(chain_id) not in RPC_URLS:
            return jsonify({'error': f'chain_id {chain_id} is not supported'}), 404

        if not address.startswith('0x') or len(address) != 42:
            return jsonify({'error': 'address must be a valid EVM address (0x + 40 hex characters)'}), 404

        try:
            analyzer = current_app.analyzer
            fund_flow = analyzer.get_fund_flow_by_address(chain_id=chain_id, address=address)
            return jsonify({'data': fund_flow}), 200
        except Exception as e:
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

    @app.route('/api/analysis/bridge', methods=['GET'])
    def get_bridge_analysis():
        chain_id = request.args.get('chain_id')
        tx_hash = request.args.get('tx_hash')

        if not chain_id:
            return jsonify({'error': 'chain_id is required'}), 400

        if not tx_hash:
            return jsonify({'error': 'tx_hash is required'}), 400

        try:
            chain_id = int(chain_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'chain_id must be a valid integer'}), 400

        try:
            analyzer = current_app.analyzer
            result = analyzer.analyze_bridge_transaction(chain_id=chain_id, tx_hash=tx_hash)
            return jsonify({'data': result}), 200
        except Exception as e:
            return jsonify({'error': f'Analyze bridge failed: {str(e)}'}), 500

    @app.route('/api/analysis/scoring', methods=['GET'])
    def get_scoring_analysis():
        chain_id = request.args.get('chain_id')
        address = request.args.get('address')
        hop_count = request.args.get('hop_count', '1')

        if not chain_id:
            return jsonify({'error': 'chain_id is required'}), 400

        if not address:
            return jsonify({'error': 'address is required'}), 400

        try:
            chain_id = int(chain_id)
            hop_count = int(hop_count)
        except ValueError:
            return jsonify({'error': 'chain_id and hop_count must be valid integers'}), 400

        if str(chain_id) not in RPC_URLS:
            return jsonify({'error': f'chain_id {chain_id} is not supported'}), 404

        if not address.startswith('0x') or len(address) != 42:
            return jsonify({'error': 'address must be a valid EVM address (0x + 40 hex characters)'}), 404

        if hop_count < 1:
            return jsonify({'error': 'hop_count must be at least 1'}), 400

        try:
            analyzer = current_app.analyzer
            graph_data = analyzer.get_multihop_fund_flow_for_scoring(
                chain_id=chain_id,
                address=address,
                hop_count=hop_count
            )
            return jsonify({'data': graph_data}), 200
        except Exception as e:
            return jsonify({'error': f'Scoring analysis failed: {str(e)}'}), 500

    return app