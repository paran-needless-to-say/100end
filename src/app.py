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
    # 개발 환경: 모든 origin 허용 (운영 환경에서는 특정 origin만 허용)
    import os
    
    # 허용할 origin 리스트 (개발 및 테스트용)
    allowed_origins = [
        # 로컬 개발 환경
        "http://localhost:3000",
        "http://localhost:5173",  # 원본 프론트엔드 (Vite 기본 포트)
        "http://localhost:5174",  # 커스텀 프론트엔드
        "http://localhost:5175",  # 추가 개발 포트
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        # EC2 배포 환경
        "http://3.38.112.25:5173",  # 원본 프론트엔드 (EC2)
        "http://3.38.112.25:5174",  # 커스텀 프론트엔드 (EC2)
        "http://3.38.112.25:80",
        "https://3.38.112.25:5173",
        "https://3.38.112.25:5174",
        # Vercel 배포
        "https://trace-x-two.vercel.app",
        "https://trace-x-two.vercel.app/",
    ]
    
    # 개발 환경 또는 ALLOW_ALL_ORIGINS=true일 때 모든 origin 허용
    if os.getenv("FLASK_ENV") == "development" or os.getenv("ALLOW_ALL_ORIGINS") == "true":
        CORS(
            app,
            origins="*",  # 개발 환경: 모든 origin 허용 (로컬 테스트 용이)
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
    app.analyzer = Analyzer(api_key=api_key)

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Docker healthcheck"""
        return jsonify({'status': 'ok', 'service': 'trace-x-backend'}), 200

    @app.route('/api/dashboard/summary', methods=['GET'])
    def get_dashboard_summary():
        # 프론트엔드가 기대하는 구조로 응답 반환
        return jsonify({
            'data': {
                'totalVolume': {
                    'value': 0,
                    'changeRate': '0'
                },
                'totalTransactions': {
                    'value': 0,
                    'changeRate': '0'
                },
                'highRiskTransactions': {
                    'value': 0,
                    'changeRate': '0'
                },
                'warningTransactions': {
                    'value': 0,
                    'changeRate': '0'
                },
                'highRiskTransactionTrend': {},
                'highRiskTransactionsByChain': {},
                'averageRiskScore': {}
            }
        }), 200

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
                from src.api.live_detection import fetch_live_detection
                
                results = fetch_live_detection(
                    token_filter=None,  # 모든 토큰
                    page_no=1,
                    page_size=3  # 최근 3개만
                )
                
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
                        
                        formatted.append({
                            "chain": "ethereum",
                            "txHash": transfer.get("txHash", ""),
                            "timestamp": formatted_timestamp,
                            "value": f"${usd_value:,.2f}"
                        })
                    except Exception as e:
                        print(f"Error formatting transfer: {e}")
                        continue
                
                return jsonify({
                    "RecentHighValueTransfers": formatted,
                }), 200

        except Exception as e:
            # 모든 API 실패 시 빈 리스트 반환 (프론트엔드가 더미 데이터 사용)
            print(f"❌ Error in get_dashboard_monitoring: {e}")
            return jsonify({
                "RecentHighValueTransfers": [],
            }), 200

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