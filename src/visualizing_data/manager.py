from datetime import datetime
from ..extensions import db
from .models import RiskAggregate

class BufferManager:
    def __init__(self):
        self.reset_buffer()

    def reset_buffer(self):
        self.buffer = {
            "start_time": datetime.utcnow(), # 기본값은 현재 시간이지만, 데이터 들어오면 바뀜
            "risk_score_sum": 0,
            "risk_score_count": 0,
            "warning_count": 0,
            "high_risk_count": 0,
            "high_risk_value_sum": 0.0,
            "chain_counts": {}
        }

    def parse_time(self, ts):
        if not ts: return None
        try:
            return datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        except:
            return None

    def add_data(self, data):
        try:

            score = data.get('risk_score', 0)
            if score is not None:
                self.buffer['risk_score_sum'] += int(score)
                self.buffer['risk_score_count'] += 1

            level = str(data.get('risk_level', '')).lower()
            val = float(data.get('value', 0.0))

            if level == 'medium':
                self.buffer['warning_count'] += 1
            elif level in ['high', 'critical']:
                self.buffer['high_risk_count'] += 1
                self.buffer['high_risk_value_sum'] += val

            chain_id = data.get('chain_id')
            if chain_id is not None:
                cid = int(chain_id) if str(chain_id).isdigit() else chain_id
                self.buffer['chain_counts'][cid] = self.buffer['chain_counts'].get(cid, 0) + 1
        except Exception as e:
            print(f"Buffer Add Error: {e}")

    def flush_to_db(self):
        if self.buffer['risk_score_count'] == 0:
            self.reset_buffer()
            return
        
        try:
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
