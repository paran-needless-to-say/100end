from flask import Flask, jsonify, request, current_app
from src.api.analysis import Analyzer


def create_app(api_key: str) -> Flask:
    app = Flask(__name__)
    app.analyzer = Analyzer(api_key=api_key)

    @app.route('/api/dashboard/summary', methods=['GET'])
    def get_dashboard_summary():
        return jsonify({'message': 'Not implemented'}), 501

    @app.route('/api/dashboard/monitoring', methods=['GET'])
    def get_dashboard_monitoring():
        return jsonify({'message': 'Not implemented'}), 501

    @app.route('/api/live-detection/summary', methods=['GET'])
    def get_live_detection_summary():
        return jsonify({'message': 'Not implemented'}), 501

    @app.route('/api/analysis/fund-flow', methods=['GET'])
    def get_fund_flow_analysis():
        chain_id = request.args.get('chainId')
        address = request.args.get('address')

        if not chain_id:
            return jsonify({'error': 'chainId is required'}), 400

        if not address:
            return jsonify({'error': 'address is required'}), 400

        try:
            chain_id = int(chain_id)
        except ValueError:
            return jsonify({'error': 'chainId must be a valid integer'}), 400

        try:
            analyzer = current_app.analyzer
            fund_flow = analyzer.get_fund_flow_by_address(chain_id=chain_id, address=address)
            return jsonify({'data': fund_flow}), 200
        except Exception as e:
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

    @app.route('/api/analysis/bridge', methods=['POST'])
    def get_bridge_analysis():
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        if data.get('tx_type') != 'BRIDGE':
            return jsonify({'error': 'tx_type must be BRIDGE'}), 400

        required_fields = ['tx_hash', 'from_address', 'to_address', 'amount',
                          'timestamp', 'token_address', 'token_symbol', 'tx_type']
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        try:
            analyzer = current_app.analyzer
            result = analyzer.analyze_bridge_transaction(tx=data)
            return jsonify({'data': result}), 200
        except Exception as e:
            return jsonify({'error': f'Analyze bridge failed: {str(e)}'}), 500

    return app