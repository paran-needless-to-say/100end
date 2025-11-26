from flask import Blueprint, jsonify, request
from src.api.reports import (
    create_report,
    get_report,
    get_all_reports,
    update_report_status
)

bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@bp.route('/suspicious', methods=['POST'])
def submit_suspicious():
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        required_fields = ['title', 'address', 'chain_id', 'risk_score', 'risk_level', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        report = create_report(
            title=data['title'],
            address=data['address'],
            chain_id=data['chain_id'],
            risk_score=data['risk_score'],
            risk_level=data['risk_level'],
            description=data['description'],
            analysis_data=data.get('analysis_data'),
            transaction_hashes=data.get('transaction_hashes', [])
        )

        return jsonify({'data': report}), 201

    except Exception as e:
        return jsonify({'error': f'Failed to create report: {str(e)}'}), 500

@bp.route('/suspicious', methods=['GET'])
def get_suspicious_list():
    try:
        status = request.args.get('status')
        chain_id = request.args.get('chain_id', type=int)
        limit = request.args.get('limit', 50, type=int)

        reports = get_all_reports(
            status=status,
            chain_id=chain_id,
            limit=limit
        )

        return jsonify({'data': reports}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get reports: {str(e)}'}), 500

@bp.route('/suspicious/<int:report_id>', methods=['GET'])
def get_suspicious_detail(report_id: int):
    try:
        report = get_report(report_id)

        if not report:
            return jsonify({'error': 'Report not found'}), 404

        return jsonify({'data': report}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get report: {str(e)}'}), 500

@bp.route('/suspicious/<int:report_id>/status', methods=['PUT'])
def update_suspicious_status(report_id: int):
    try:
        data = request.get_json()

        if not data or 'status' not in data:
            return jsonify({'error': 'Missing status field'}), 400

        status = data['status']
        if status not in ['pending', 'reviewed', 'resolved']:
            return jsonify({'error': 'Invalid status. Must be one of: pending, reviewed, resolved'}), 400

        report = update_report_status(report_id, status)

        if not report:
            return jsonify({'error': 'Report not found'}), 404

        return jsonify({'data': report}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to update report status: {str(e)}'}), 500
