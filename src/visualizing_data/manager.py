from datetime import datetime
from collections import defaultdict
from ..extensions import db
from .models import RiskAggregate

CHAIN_ID_MAP = { 1: "Ethereum", 0: "Bitcoin", 8453: "Base" }

class BufferManager:
    def __init__(self):
        self.reset_buffer()

    def reset_buffer(self):
        self.buffer = {
            "start_time": datetime.utcnow(),
            "risk_score_sum": 0,
            "risk_score_count": 0,
            "warning_count": 0,
            "high_risk_count": 0,
            "high_risk_value_sum": 0.0,
            "chain_counts": defaultdict(int)
        }

    def add_data(self, data):
        print(f"👀 [Manager] 데이터 수신! 구조 확인 중...")
        
        if not data or 'data' not in data or 'nodes' not in data['data']:
            print("❌ [Manager] 데이터 구조가 이상합니다 (nodes 없음)")
            return
        
        try:
            node = data['data']['nodes'][0]
            risk = node.get('risk', {})
            
            score = risk.get("risk_score", 0)
            raw_level = risk.get("risk_level", "")
            level = str(raw_level).lower()
            
            val = float(risk.get("amount_usd", 0.0) or 0.0)
            
            raw_cid = node.get("chain_id")
            try:
                c_id = int(raw_cid)
            except:
                c_id = -1

            print(f"✅ [Manager] 추출 성공! Level: '{level}' (원본: {raw_level}), Value: {val}, ChainID: {c_id}")

            self.buffer["risk_score_sum"] += score
            self.buffer["risk_score_count"] += 1

            if level in ["medium", "high", "critical"]:
                self.buffer["warning_count"] += 1
            
            if level in ["high", "critical"]:
                self.buffer["high_risk_count"] += 1
                self.buffer["high_risk_value_sum"] += val
                print(f"💰 [Manager] High Risk 금액 누적! 현재 합계: {self.buffer['high_risk_value_sum']}")
            else:
                print(f"⚠️ [Manager] High Risk 조건 불만족 (Level이 '{level}'임)")

            chain_name = CHAIN_ID_MAP.get(c_id, "Others")
            self.buffer["chain_counts"][chain_name] += 1
            print(f"🔗 [Manager] 체인 분류: {chain_name} (ID: {c_id})")
            
        except Exception as e:
            print(f"⚠️ [Manager] 파싱 에러: {e}")

    def flush_to_db(self):
        if self.buffer["risk_score_count"] == 0:
            print("💤 [Flush] 저장할 데이터가 없습니다.")
            return

        try:
            new_agg = RiskAggregate(
                timestamp=datetime.utcnow(),
                total_risk_score=self.buffer["risk_score_sum"],
                risk_score_count=self.buffer["risk_score_count"],
                warning_tx_count=self.buffer["warning_count"],
                high_risk_tx_count=self.buffer["high_risk_count"],
                high_risk_value_sum=self.buffer["high_risk_value_sum"],
                chain_data=self.buffer["chain_counts"]
            )
            db.session.add(new_agg)
            db.session.commit()
            print(f"💾 [Flush] DB 저장 완료! (Count: {self.buffer['risk_score_count']}, Value: {self.buffer['high_risk_value_sum']})")
        except Exception as e:
            print(f"❌ [Flush] DB 에러: {e}")
            db.session.rollback()
        finally:
            self.reset_buffer()

buffer_manager = BufferManager()
