#json 형식 (11.23)
from ..extensions import db 
from datetime import datetime
from datetime import datetime

from datetime import datetime
from ..extensions import db

# 1. 원본 데이터 저장용
class RawTransaction(db.Model):
    __tablename__ = 'raw_transactions'  # [확인] 복수형 (s 붙음)
    
    id = db.Column(db.Integer, primary_key=True)
    target_address = db.Column(db.String(255))
    risk_score = db.Column(db.Integer)
    risk_level = db.Column(db.String(50))
    chain_id = db.Column(db.Integer)
    value = db.Column(db.Float)
    timestamp = db.Column(db.DateTime)
    
    # 전체 JSON 저장
    raw_data = db.Column(db.JSON)

class RiskAggregate(db.Model):
    """2. 통계 요약 저장용 (10분 단위 집계)"""
    __tablename__ = 'risk_aggregates'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True) # 해당 10분 구간 시작 시간

    # 평균 점수 계산용
    total_risk_score = db.Column(db.Integer, default=0)
    risk_score_count = db.Column(db.Integer, default=0)

    # 카운트 집계
    warning_tx_count = db.Column(db.Integer, default=0)   # Medium 이상
    high_risk_tx_count = db.Column(db.Integer, default=0) # High, Critical
    
    # Value 집계
    high_risk_value_sum = db.Column(db.Float, default=0.0)

    # 체인별 카운트 (JSON으로 저장: {"Ethereum": 10, "Base": 5})
    chain_data = db.Column(db.JSON, default=dict)