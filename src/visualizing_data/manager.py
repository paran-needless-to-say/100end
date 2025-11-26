from datetime import datetime
from ..extensions import db
from .models import RiskAggregate

class BufferManager:
    def __init__(self):
        self.reset_buffer()

    def reset_buffer(self):
        """버퍼 초기화"""
        self.buffer = {
            "start_time": datetime.utcnow(), # 기본값은 현재 시간이지만, 데이터 들어오면 바뀜
            "risk_score_sum": 0,
            "risk_score_count": 0,
            "warning_count": 0,
            "high_risk_count": 0,
            "high_risk_value_sum": 0.0,
            "chain_counts": {}
        }

<<<<<<< HEAD
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
=======
    def parse_time(self, ts):
        if not ts: return None
        try:
            return datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        except:
            return None

    def add_data(self, data):
        """
        데이터를 버퍼에 추가하고, 버퍼의 시간을 데이터 시간으로 동기화
        """
        try:

            # 1. Score 집계
            score = data.get('risk_score', 0)
            if score is not None:
                self.buffer['risk_score_sum'] += int(score)
                self.buffer['risk_score_count'] += 1
>>>>>>> feature/dashboard-api

            # 2. Risk Level 집계
            level = str(data.get('risk_level', '')).lower()
            val = float(data.get('value', 0.0))

            if level == 'medium':
                self.buffer['warning_count'] += 1
            elif level in ['high', 'critical']:
                self.buffer['high_risk_count'] += 1
                self.buffer['high_risk_value_sum'] += val

            # 3. Chain 집계
            chain_id = data.get('chain_id')
            if chain_id is not None:
                cid = int(chain_id) if str(chain_id).isdigit() else chain_id
                self.buffer['chain_counts'][cid] = self.buffer['chain_counts'].get(cid, 0) + 1

<<<<<<< HEAD
            chain_name = CHAIN_ID_MAP.get(c_id, "Others")
            self.buffer["chain_counts"][chain_name] += 1
            print(f"🔗 [Manager] 체인 분류: {chain_name} (ID: {c_id})")
            
=======
>>>>>>> feature/dashboard-api
        except Exception as e:
            print(f"Buffer Add Error: {e}")

    def flush_to_db(self):
        if self.buffer['risk_score_count'] == 0:
            self.reset_buffer()
            return
        
        try:
            # 저장 시 self.buffer['start_time']을 사용하므로, 
            # 위에서 덮어쓴 2025-11-19 시간이 들어감
            agg = RiskAggregate(
                timestamp=self.buffer['start_time'], 
                total_risk_score=self.buffer['risk_score_sum'],
                risk_score_count=self.buffer['risk_score_count'],
                warning_tx_count=self.buffer['warning_count'],
                high_risk_tx_count=self.buffer['high_risk_count'],
                high_risk_value_sum=self.buffer['high_risk_value_sum'],
                chain_data=self.buffer['chain_counts']
            )
            db.session.add(agg)
            db.session.commit()
            print(f"✅ Flushed buffer to DB with time: {self.buffer['start_time']}")
        except Exception as e:
            print(f"Flush Error: {e}")
            db.session.rollback()
        finally:
            self.reset_buffer()

buffer_manager = BufferManager()
