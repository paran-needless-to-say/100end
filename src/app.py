import os
from datetime import datetime

from flask import Flask, jsonify, request, current_app
from flask_cors import CORS
from dotenv import load_dotenv

# 원격에서 온 API 관련 import
from src.api.analysis import Analyzer
from src.api.live_detection import fetch_live_detection
from src.api.dashboard import get_dune_results, LOCAL_CACHE
from src.api.risk_scoring import analyze_address_with_risk_scoring

# 로컬에서 추가한 DB/확장 관련 import
from .extensions import db, migrate

load_dotenv()


def create_app(api_key: str) -> Flask:
    app = Flask(__name__)

    # ------------------------------
    # 🔵 로컬에서 추가한 JSON 설정
    # ------------------------------
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    app.config['JSON_AS_ASCII'] = False

    # ------------------------------
    # 🔵 로컬 DB 설정 + 초기화
    # ------------------------------
    db_host = os.getenv('DB_HOST')
    db_user = os.getenv('DB_USER')
    db_pass = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')
    db_port = '3306'

    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f'mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')

    # DB 초기화
    db.init_app(app)
    migrate.init_app(app, db)

    # 모델 로딩
    from .visualizing_data import models

    # ------------------------------
    # 🔵 원격에 있던 CORS 설정 (EC2 + Vercel 지원)
    # ------------------------------
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://3.38.112.25:5173",
        "http://3.38.112.25:5174",
        "http://3.38.112.25:80",
        "https://3.38.112.25:5173",
        "https://3.38.112.25:5174",
        "https://trace-x-two.vercel.app",
        "https://trace-x-two.vercel.app/",
    ]

    if os.getenv("FLASK_ENV") == "development" or os.getenv("ALLOW_ALL_ORIGINS") == "true":
        CORS(
            app,
            origins="*",
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "Cache-Control", "Pragma"],
            supports_credentials=False,  # "*" origin일 때는 credentials 불가
        )
    else:
        CORS(
            app,
            origins=allowed_origins,
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization", "Cache-Control", "Pragma"],
            supports_credentials=True,
        )

    # ------------------------------
    # 🔵 Analyzer 객체 초기화
    # ------------------------------
    app.analyzer = Analyzer(api_key=api_key)

    # ------------------------------
    # 🔵 Health Check
    # ------------------------------
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'ok', 'service': 'trace-x-backend'}), 200

    # ------------------------------
    # 🔵 Dashboard Summary (원격)
    # ------------------------------
    @app.route('/api/dashboard/summary', methods=['GET'])
    def get_dashboard_summary():
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

    # ------------------------------
    # 🔵 Dune Monitoring (원격)
    # ------------------------------
    @app.route('/api/dashboard/monitoring', methods=['GET'])
    def get_dashboard_monitoring():
        """
        최근 고액 거래 데이터 반환
        1. Dune API에서 데이터를 먼저 시도
        2. Dune API 실패 시 Alchemy API (live-detection)를 fallback으로 사용
        """
        try:
            # 1. 먼저 Dune API 시도
            from src.api.dashboard import get_dune_results
            rows = get_dune_results()
            
            if rows and len(rows) > 0:
                # Dune API 성공 - 기존 로직 사용
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
            else:
                # 2. Dune API 실패 또는 데이터 없음 - Alchemy API fallback
                print("⚠️  Dune API 결과 없음, Alchemy API로 fallback...")
                try:
                    from src.api.live_detection import fetch_live_detection
                    
                    results = fetch_live_detection(
                        token_filter=None,  # 모든 토큰
                        page_no=1,
                        page_size=3  # 최근 3개만
                    )
                    
                    if not results or len(results) == 0:
                        print("⚠️  Alchemy API도 데이터를 반환하지 않았습니다.")
                        return jsonify({
                            "RecentHighValueTransfers": [],
                        }), 200
                    
                    print(f"✅ Alchemy API fallback 성공 (데이터: {len(results)}개)")
                    
                    formatted = []
                    for transfer in results:
                        # timestamp를 프론트엔드 형식으로 변환
                        dt = datetime.fromtimestamp(transfer["timestamp"])
                        formatted_timestamp = dt.strftime("%b %d, %I:%M %p")
                        
                        # USD 가치 계산 (간단한 추정)
                        try:
                            amount = float(transfer.get("amount", 0))
                            token = transfer.get("token", "")
                            
                            # 토큰별 대략적 USD 가격 (간단한 추정값)
                            # 실제로는 CoinGecko API 등을 사용하는 것이 좋음
                            token_prices = {
                                "ETH": 3000.0,
                                "USDT": 1.0,
                                "USDC": 1.0,
                                "DAI": 1.0,
                            }
                            
                            # 토큰 심볼 추출 (예: "ETH" 또는 "0x...")
                            price = token_prices.get(token.upper(), 1.0)
                            if not token or token.startswith("0x"):
                                # 컨트랙트 주소인 경우 기본값 사용
                                price = 1.0
                            
                            usd_value = amount * price
                            
                            # 최소 $1 이상인 거래만 포함 (노이즈 제거)
                            if usd_value >= 1.0:
                                formatted.append({
                                    "chain": "ethereum",
                                    "txHash": transfer.get("txHash", ""),
                                    "timestamp": formatted_timestamp,
                                    "value": f"${usd_value:,.2f}"
                                })
                        except Exception as e:
                            print(f"⚠️  Error formatting transfer: {e}")
                            continue
                    
                    # 최대 3개만 반환
                    formatted = formatted[:3]
                    
                    return jsonify({
                        "RecentHighValueTransfers": formatted,
                    }), 200
                except Exception as e:
                    print(f"❌ Alchemy API fallback 오류: {e}")
                    return jsonify({
                        "RecentHighValueTransfers": [],
                    }), 200

              formatted = [{
                  "chain": row["chain"],
                  "txHash": row["tx_hash"],
                  "timestamp": datetime.fromtimestamp(
                      row["display_timestamp"]
                  ).strftime("%b %d, %I:%M %p"),
                  "value": f"${row['value_usd']:,.0f}"
              } for row in rows]
            
            return jsonify({
                "RecentHighValueTransfers": [],
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

    # ------------------------------
    # 🔵 Transaction Flow Analysis (원격)
    # ------------------------------
    @app.route('/api/analysis/transaction-flow', methods=['GET'])
    def get_transaction_flow_analysis():
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

    # ------------------------------
    # 🔵 Fund Flow Analysis (원격)
    # ------------------------------
    @app.route('/api/analysis/fund-flow', methods=['GET'])
    def get_fund_flow_analysis():
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

    # ------------------------------
    # 🔵 Bridge Analysis (원격)
    # ------------------------------
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

    # ------------------------------
    # 🔵 Scoring Analysis (원격)
    # ------------------------------
    @app.route('/api/analysis/scoring', methods=['GET', 'POST'])
    def get_scoring_analysis():
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

    # ------------------------------
    # 🔵 Risk Scoring (원격)
    # ------------------------------
    @app.route('/api/analysis/risk-scoring', methods=['GET', 'POST'])
    def get_risk_scoring_analysis():
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
            return jsonify({'error': 'analysis_type must be \"basic\" or \"advanced\"'}), 400

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

    # ------------------------------
    # 🔵 Blueprint 등록 + DB 생성 (로컬 추가)
    # ------------------------------
    from .visualizing_data import bp as visualizing_bp
    app.register_blueprint(visualizing_bp)

    with app.app_context():
        from .visualizing_data import models
        db.create_all()

    return app
  
    # 의심거래 보고서 API
    from src.api.reports import (
        create_report,
        get_report,
        get_all_reports,
        update_report_status
    )

    @app.route('/api/reports/suspicious', methods=['POST'])
    def submit_suspicious_report():
        """의심거래 보고서 작성/제출"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            # 필수 필드 확인
            required_fields = ['title', 'address', 'chain_id', 'risk_score', 'risk_level', 'description']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # 보고서 생성
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

    @app.route('/api/reports/suspicious', methods=['GET'])
    def get_suspicious_reports():
        """의심거래 보고서 목록 조회"""
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

    @app.route('/api/reports/suspicious/<int:report_id>', methods=['GET'])
    def get_suspicious_report_detail(report_id: int):
        """특정 보고서 상세 조회"""
        try:
            report = get_report(report_id)
            
            if not report:
                return jsonify({'error': 'Report not found'}), 404
            
            return jsonify({'data': report}), 200
            
        except Exception as e:
            return jsonify({'error': f'Failed to get report: {str(e)}'}), 500

    @app.route('/api/reports/suspicious/<int:report_id>/status', methods=['PUT'])
    def update_suspicious_report_status(report_id: int):
        """보고서 상태 업데이트"""
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

    return app
