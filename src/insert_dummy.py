from datetime import datetime, timedelta
import random

from src.app import create_app
from src.visualizing_data.models import RiskAggregate
from src.extensions import db


# -----------------------------
#  시즌/시간대 패턴 설정
# -----------------------------

PATTERN_MULTIPLIER = {
    1: 0.7, 2: 0.8, 3: 0.9,           # 1~3월: Low risk
    4: 1.1, 5: 1.2, 6: 1.3,           # 4~6월: 점진 상승
    7: 1.6, 8: 1.8,                   # 7~8월: High peak
    9: 1.2, 10: 1.1,                  # 9~10월: 안정기
    11: 2.0,                          # 11월: 공격 시즌
    12: 1.0                           # 12월: 보통
}

TIME_MULTIPLIER = {
    0: 0.9, 2: 0.8, 4: 0.7, 6: 0.8,   # 새벽: 위험 낮음
    8: 1.0, 10: 1.1, 12: 1.2, 14: 1.3,
    16: 1.4, 18: 1.5, 20: 1.6, 22: 1.3
}

INTERVAL_MINUTES = 10


def generate_chain_data(month: int) -> dict:
    base_factor = 1.2 if month in [7, 8, 9] else 1.0

    return {
        "1": random.randint(3, 10),
        "8453": int(random.randint(1, 5) * base_factor),
        "0": random.randint(0, 2),
    }


def main():
    app = create_app(api_key="dummy")

    with app.app_context():
        print("📌 기존 RiskAggregate 데이터 삭제 중…")
        db.session.query(RiskAggregate).delete()
        db.session.commit()
        print("✅ 삭제 완료")

        start_time = datetime.utcnow() - timedelta(days=365)
        current_time = start_time

        total_minutes = 365 * 24 * 60
        steps = total_minutes // INTERVAL_MINUTES

        print(f"📌 1년치 더미 생성 시작 (약 {steps} rows)…")

        inserted = 0

        for i in range(int(steps)):
            month = current_time.month
            hour_slot = (current_time.hour // 2) * 2

            season_factor = PATTERN_MULTIPLIER.get(month, 1.0)
            hour_factor = TIME_MULTIPLIER.get(hour_slot, 1.0)
            multiplier = season_factor * hour_factor

            risk_score_count = random.randint(5, 15)
            base_risk = random.randint(80, 220)
            total_risk_score = int(base_risk * multiplier)

            warning_count = int(risk_score_count * random.uniform(0.1, 0.3))
            high_count = int(risk_score_count * random.uniform(0.05, 0.2))

            high_risk_value_sum = round(
                (random.uniform(300, 2500) * max(high_count, 1)) * multiplier,
                2
            )

            agg = RiskAggregate(
                timestamp=current_time,
                total_risk_score=total_risk_score,
                risk_score_count=risk_score_count,
                warning_tx_count=warning_count,
                high_risk_tx_count=high_count,
                high_risk_value_sum=high_risk_value_sum,
                chain_data=generate_chain_data(month),
            )

            db.session.add(agg)
            inserted += 1

            if i % 200 == 0:
                db.session.commit()
                print(f"  ... {inserted}개 생성됨 ({current_time})")

            current_time += timedelta(minutes=INTERVAL_MINUTES)

        db.session.commit()
        print(f"🎉 완료! 총 {inserted}개의 더미 데이터를 생성했습니다.")


if __name__ == "__main__":
    main()
