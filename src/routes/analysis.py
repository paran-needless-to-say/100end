from flask import Blueprint, jsonify, request, current_app
from src.api.risk_scoring import analyze_address_with_risk_scoring

bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')

@bp.route('/transaction-flow', methods=['GET'])
def get_transaction_flow():
    chain_id = request.args.get('chain_id')
    tx_hash = request.args.get('tx_hash')
    max_hops = request.args.get('max_hops', '3')

    if not chain_id:
        return jsonify({'error': 'chain_id is required'}), 400
    if not tx_hash:
        return jsonify({'error': 'tx_hash is required'}), 400

    try:
        chain_id = int(chain_id)
        max_hops = int(max_hops)
    except ValueError:
        return jsonify({'error': 'chain_id and max_hops must be valid integers'}), 400

    try:
        analyzer = current_app.analyzer
        flow_data = analyzer.get_transaction_fund_flow(
            chain_id=chain_id,
            tx_hash=tx_hash,
            max_hops=max_hops
        )
        return jsonify({'data': flow_data}), 200
    except Exception as e:
        return jsonify({'error': f'Transaction analysis failed: {str(e)}'}), 500

@bp.route('/fund-flow', methods=['GET'])
def get_fund_flow():
    chain_id = request.args.get('chain_id')
    address = request.args.get('address')
    max_hops = request.args.get('max_hops', '2')
    max_addresses = request.args.get('max_addresses', '10')

    if not chain_id:
        return jsonify({'error': 'chain_id is required'}), 400
    if not address:
        return jsonify({'error': 'address is required'}), 400

    try:
        chain_id = int(chain_id)
        max_hops = int(max_hops)
        max_addresses = int(max_addresses)
    except ValueError:
        return jsonify({'error': 'chain_id, max_hops, and max_addresses must be valid integers'}), 400

    try:
        analyzer = current_app.analyzer
        fund_flow = analyzer.get_multihop_fund_flow_for_scoring(
            chain_id=chain_id,
            address=address,
            max_hops=max_hops,
            max_addresses_per_direction=max_addresses
        )
        return jsonify({'data': fund_flow}), 200
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@bp.route('/bridge', methods=['GET'])
def get_bridge():
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

@bp.route('/scoring', methods=['GET', 'POST'])
def get_scoring():
    if request.method == 'GET':
        chain_id = request.args.get('chain_id')
        address = request.args.get('address')
        hop_count = request.args.get('hop_count', '3')
        max_hops = hop_count
        max_addresses_per_direction = request.args.get('max_addresses_per_direction', '10')
    else:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        chain_id = data.get('chain_id')
        address = data.get('address')
        max_hops = data.get('max_hops', data.get('hop_count', 3))
        max_addresses_per_direction = data.get('max_addresses_per_direction', 10)

    if not chain_id:
        return jsonify({'error': 'chain_id is required'}), 400
    if not address:
        return jsonify({'error': 'address is required'}), 400

    try:
        chain_id = int(chain_id)
        max_hops = int(max_hops)
        max_addresses_per_direction = int(max_addresses_per_direction)
    except (ValueError, TypeError):
        return jsonify({'error': 'chain_id, max_hops/hop_count, and max_addresses_per_direction must be valid integers'}), 400

    try:
        analyzer = current_app.analyzer
        graph_data = analyzer.get_multihop_fund_flow_for_scoring(
            chain_id=chain_id,
            address=address,
            max_hops=max_hops,
            max_addresses_per_direction=max_addresses_per_direction
        )
        return jsonify({'data': graph_data}), 200
    except Exception as e:
        return jsonify({'error': f'Scoring analysis failed: {str(e)}'}), 500

@bp.route('/risk-scoring', methods=['GET', 'POST'])
def get_risk_scoring():
    if request.method == 'GET':
        chain_id = request.args.get('chain_id')
        address = request.args.get('address')
        hop_count = request.args.get('hop_count', '3')
        max_hops = hop_count
        max_addresses_per_direction = request.args.get('max_addresses_per_direction', '10')
        analysis_type = request.args.get('analysis_type', 'basic')
    else:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        chain_id = data.get('chain_id')
        address = data.get('address')
        max_hops = data.get('max_hops', data.get('hop_count', 3))
        max_addresses_per_direction = data.get('max_addresses_per_direction', 10)
        analysis_type = data.get('analysis_type', 'basic')

    if not chain_id:
        return jsonify({'error': 'chain_id is required'}), 400
    if not address:
        return jsonify({'error': 'address is required'}), 400

    if analysis_type not in ['basic', 'advanced']:
        return jsonify({'error': 'analysis_type must be "basic" or "advanced"'}), 400

    try:
        chain_id = int(chain_id)
        max_hops = int(max_hops)
        max_addresses_per_direction = int(max_addresses_per_direction)
    except (ValueError, TypeError):
        return jsonify({'error': 'chain_id, max_hops/hop_count, and max_addresses_per_direction must be valid integers'}), 400

    try:
        analyzer = current_app.analyzer

        graph_data = analyzer.get_multihop_fund_flow_for_scoring(
            chain_id=chain_id,
            address=address,
            max_hops=max_hops,
            max_addresses_per_direction=max_addresses_per_direction
        )

        result = analyze_address_with_risk_scoring(
            address=address,
            chain_id=chain_id,
            graph_data=graph_data,
            analysis_type=analysis_type
        )
        return jsonify({'data': result}), 200
    except Exception as e:
        return jsonify({'error': f'Risk scoring failed: {str(e)}'}), 500
