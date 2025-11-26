from flask import Blueprint, jsonify, request
from src.api.live_detection import fetch_live_detection

bp = Blueprint('live_detection', __name__, url_prefix='/api/live-detection')

@bp.route('/summary', methods=['GET'])
def get_summary():
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
