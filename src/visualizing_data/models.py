from ..extensions import db 
from datetime import datetime
from datetime import datetime

from datetime import datetime
from ..extensions import db

class RawTransaction(db.Model):
    __tablename__ = 'raw_transactions'  # [확인] 복수형 (s 붙음)
    
    id = db.Column(db.Integer, primary_key=True)
    target_address = db.Column(db.String(255))
    risk_score = db.Column(db.Integer)
    risk_level = db.Column(db.String(50))
    chain_id = db.Column(db.Integer)
    value = db.Column(db.Float)
    timestamp = db.Column(db.DateTime)
    
    raw_data = db.Column(db.JSON)

class RiskAggregate(db.Model):
    __tablename__ = 'risk_aggregates'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True)

    total_risk_score = db.Column(db.Integer, default=0)
    risk_score_count = db.Column(db.Integer, default=0)

    warning_tx_count = db.Column(db.Integer, default=0)
    high_risk_tx_count = db.Column(db.Integer, default=0)
    
    high_risk_value_sum = db.Column(db.Float, default=0.0)

    chain_data = db.Column(db.JSON, default=dict)
