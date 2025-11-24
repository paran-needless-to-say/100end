from datetime import datetime

from flask import Flask, jsonify, request, current_app
from flask_cors import CORS
from src.api.analysis import Analyzer
from src.api.live_detection import fetch_live_detection
from src.api.dashboard import get_dune_results, LOCAL_CACHE
from src.api.risk_scoring import analyze_address_with_risk_scoring


def create_app(api_key: str) -> Flask:
    app = Flask(__name__)
    # CORS 설정 명시적으로 추가 (OPTIONS preflight 요청 처리)
    CORS(
        app,
        origins=[
            "http://localhost:5173", 
            "https://trace-x-two.vercel.app/",
            "http://3.38.112.25:5173",
            "http://3.38.112.25:80"
        ],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True,
    )
    app.analyzer = Analyzer(api_key=api_key)

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Docker healthcheck"""
        return jsonify({'status': 'ok', 'service': 'trace-x-backend'}), 200

    @app.route('/api/dashboard/summary', methods=['GET'])
    def get_dashboard_summary():
        # 임시로 빈 응답 반환 (프론트엔드 호환성)
        return jsonify({
            'data': {
                'totalAddresses': 0,
                'totalTransactions': 0,
                'totalRiskScore': 0,
                'averageRiskScore': {}
            }
        }), 200

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

    @app.route('/api/analysis/transaction-flow', methods=['GET'])
    def get_transaction_flow_analysis():
        """
        트랜잭션 해시 기반 자금 흐름 분석
        
        Query Parameters:
        - chain_id: 체인 ID (required)
        - tx_hash: 트랜잭션 해시 (required)
        - max_hops: 최대 홉 수 (optional, default: 3)
        """
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
            # 트랜잭션 자금 흐름 분석
            flow_data = analyzer.get_transaction_fund_flow(
                chain_id=chain_id,
                tx_hash=tx_hash,
                max_hops=max_hops
            )
            return jsonify({'data': flow_data}), 200
        except Exception as e:
            return jsonify({'error': f'Transaction analysis failed: {str(e)}'}), 500

    @app.route('/api/analysis/fund-flow', methods=['GET'])
    def get_fund_flow_analysis():
        """
        Fund flow 그래프 데이터 가져오기 (multi-hop 지원)
        
        Query Parameters:
        - chain_id: 체인 ID (required)
        - address: 분석할 주소 (required)
        - max_hops: 최대 홉 수 (optional, default: 2)
        - max_addresses: 방향당 최대 주소 수 (optional, default: 10)
        """
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
            # Multi-hop fund flow 데이터 수집
            fund_flow = analyzer.get_multihop_fund_flow_for_scoring(
                chain_id=chain_id,
                address=address,
                max_hops=max_hops,
                max_addresses_per_direction=max_addresses
            )
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

    @app.route('/api/analysis/scoring', methods=['GET', 'POST'])  # ← GET도 추가!
    def get_scoring_analysis():
        # GET 또는 POST 파라미터 처리
        if request.method == 'GET':
            # GET: query parameters
            chain_id = request.args.get('chain_id')
            address = request.args.get('address')
            hop_count = request.args.get('hop_count', '3')  # hop_count -> max_hops
            max_hops = hop_count  # 호환성을 위해 hop_count도 허용
            max_addresses_per_direction = request.args.get('max_addresses_per_direction', '10')
        else:
            # POST: JSON body
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            chain_id = data.get('chain_id')
            address = data.get('address')
            max_hops = data.get('max_hops', data.get('hop_count', 3))  # hop_count 호환
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

    @app.route('/api/analysis/risk-scoring', methods=['GET', 'POST'])  # ← GET도 추가!
    def get_risk_scoring_analysis():
        """
        Multi-hop 데이터 수집 + 리스크 스코어링
        
        GET Request:
            /api/analysis/risk-scoring?chain_id=1&address=0x...&hop_count=3
        
        POST Request:
        {
            "address": "0x...",
            "chain_id": 1,
            "max_hops": 3,  // optional, default: 3 (또는 hop_count)
            "analysis_type": "basic" or "advanced"  // optional, default: "basic"
        }
        
        Response:
        {
            "data": {
                "address": "0x...",
                "chain": "ethereum",
                "final_score": 85,
                "risk_level": "high",
                ...
            }
        }
        """
        # GET 또는 POST 파라미터 처리
        if request.method == 'GET':
            # GET: query parameters
            chain_id = request.args.get('chain_id')
            address = request.args.get('address')
            hop_count = request.args.get('hop_count', '3')
            max_hops = hop_count  # hop_count -> max_hops
            max_addresses_per_direction = request.args.get('max_addresses_per_direction', '10')
            analysis_type = request.args.get('analysis_type', 'basic')
        else:
            # POST: JSON body
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            chain_id = data.get('chain_id')
            address = data.get('address')
            max_hops = data.get('max_hops', data.get('hop_count', 3))  # hop_count 호환
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
            # 1. Multi-hop 그래프 데이터 수집
            analyzer = current_app.analyzer
            graph_data = analyzer.get_multihop_fund_flow_for_scoring(
                chain_id=chain_id,
                address=address,
                max_hops=max_hops,
                max_addresses_per_direction=max_addresses_per_direction
            )
            
            # 2. 리스크 스코어링 API 호출
            result = analyze_address_with_risk_scoring(
                address=address,
                chain_id=chain_id,
                graph_data=graph_data,
                analysis_type=analysis_type
            )
            
            return jsonify({'data': result}), 200
        except Exception as e:
            return jsonify({'error': f'Risk scoring failed: {str(e)}'}), 500

    return app