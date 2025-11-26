import sys
import os
from datetime import datetime, timedelta
import random

sys.path.append(os.getcwd())

from src.create_app import create_app
from src.visualizing_data.models import RiskAggregate
from src.extensions import db

INTERVAL_MINUTES = 10

PATTERN_MULTIPLIER = {
    1: 0.7, 2: 0.8, 3: 0.9, 4: 1.1, 5: 1.2, 6: 1.3,
    7: 1.6, 8: 1.8, 9: 1.2, 10: 1.1, 11: 2.0, 12: 1.0
}
TIME_MULTIPLIER = {
    0: 0.9, 2: 0.8, 4: 0.7, 6: 0.8, 8: 1.0, 10: 1.1, 
    12: 1.2, 14: 1.3, 16: 1.4, 18: 1.5, 20: 1.6, 22: 1.3
}

def generate_chain_data(month: int) -> dict:
    base_factor = 1.2 if month in [7, 8, 9] else 1.0
    return {
        "1": random.randint(3, 10),
        "8453": int(random.randint(1, 5) * base_factor),
        "0": random.randint(0, 2),
        "-1": random.randint(1, 4)  # 기타 포함
    }

def create_risk_entry(current_time):
    month = current_time.month
    hour_slot = (current_time.hour // 2) * 2
    multiplier = PATTERN_MULTIPLIER.get(month, 1.0) * TIME_MULTIPLIER.get(hour_slot, 1.0)

    risk_score_count = random.randint(5, 15)
    base_risk = random.randint(80, 220)
    
    agg = RiskAggregate(
        timestamp=current_time,
        total_risk_score=int(base_risk * multiplier),
        risk_score_count=risk_score_count,
        warning_tx_count=int(risk_score_count * random.uniform(0.1, 0.3)),
        high_risk_tx_count=int(risk_score_count * random.uniform(0.05, 0.2)),
        high_risk_value_sum=round((random.uniform(300, 2500) * 1) * multiplier, 2),
        chain_data=generate_chain_data(month) 
    )
    return agg

def fill_today_missing_data():
    print("⏳ [빈 시간 채우기] 마지막 데이터 시점 확인 중...")
    
    last_record = RiskAggregate.query.order_by(RiskAggregate.timestamp.desc()).first()
    now = datetime.utcnow()
    
    if last_record:
        start_time = last_record.timestamp + timedelta(minutes=INTERVAL_MINUTES)
    else:
        start_time = datetime(now.year, now.month, now.day)

    current_time = start_time
    inserted_count = 0
    
    if current_time > now:
        print(f"✅ 이미 최신 상태입니다. (마지막 기록: {last_record.timestamp})")
        return

    print(f"📌 {start_time} 부터 {now} 까지 데이터를 생성합니다...")

    while current_time <= now:
        agg = create_risk_entry(current_time)
        db.session.add(agg)
        inserted_count += 1
        current_time += timedelta(minutes=INTERVAL_MINUTES)

    db.session.commit()
    print(f"✅ 완료! {inserted_count}개의 최신 데이터를 추가했습니다.")

def main():
    app = create_app(api_key="dummy")
    with app.app_context():
        fill_today_missing_data()

if __name__ == "__main__":
    main()