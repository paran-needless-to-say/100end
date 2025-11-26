from flask import jsonify, request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from ..extensions import db
from .models import RawTransaction, RiskAggregate
from .manager import buffer_manager
from . import bp
from .extract_transaction_and_amount import get_total_data

# ---------------------------------------------------------
# [설정] Dune 데이터 캐싱 (Total만 남김 - 에러 방지용 더미)
# ---------------------------------------------------------
DUNE_CACHE = {
    "last_updated": None,
    "data": {
        "totalVolume": {"value": 0, "changeRate": "0%"},
        "totalTransactions": {"value": 0, "changeRate": "0%"}
    }
}

def update_dune_cache_if_needed():
    now = datetime.utcnow()
    now_kst = now + timedelta(hours=9)
    # 5분 캐시
    if DUNE_CACHE["last_updated"]:
        elapsed = (now_kst - DUNE_CACHE["last_updated"]).total_seconds()
        if elapsed < 300:
            return

    # Dune 호출
    totals = get_total_data()  # 여기서 Dune API 실제로 부름

    DUNE_CACHE["data"]["totalVolume"] = totals["totalVolume"]
    DUNE_CACHE["data"]["totalTransactions"] = totals["totalTransactions"]
    DUNE_CACHE["last_updated"] = now_kst

# ---------------------------------------------------------
# [설정] 체인 및 순서 설정
# ---------------------------------------------------------
TARGET_CHAINS = ["Ethereum", "Bitcoin", "Base", "Others"]
CHAIN_ID_MAP = { 1: "Ethereum", 0: "Bitcoin", 8453: "Base" }
PERIOD_ORDER = ["1~2월", "3~4월", "5~6월", "7~8월", "9~10월", "11~12월"]
TIME_ORDER = [f"{i:02}" for i in range(0, 24, 2)]

# ---------------------------------------------------------
# 1. 데이터 수집 (Ingest) - [최종 수정됨]
# ---------------------------------------------------------

#이거 연동용 ingest 똑같이 복사함 (인자만 받는 형태)
def ingest_core(data: dict) -> dict:
    try:
        # 무조건 "지금" 기준 (KST)
        now = datetime.utcnow()
        now_kst = now + timedelta(hours=9)
        current_time = now_kst

        val = float(data.get('value', 0.0))

        tx = RawTransaction(
            target_address=data.get('target_address'),
            risk_score=data.get('risk_score'),
            risk_level=str(data.get('risk_level', '')).lower(),
            chain_id=data.get('chain_id'),
            value=val,
            timestamp=current_time,  # ✅ 항상 현재 시간으로 저장
            raw_data=data,
        )
        db.session.add(tx)
        db.session.commit()

        # 버퍼 누적 (시간은 매니저 내부에서 현재 기준으로 처리)
        buffer_manager.add_data(data)

    except Exception as e:
        print(f"⚠️ Ingest Error: {e}")

    # 플러시 체크
    start_time = buffer_manager.buffer['start_time']
    if start_time is not None and start_time.tzinfo is not None:
        start_time = start_time.replace(tzinfo=None)

    now = datetime.utcnow()
    now_kst = now + timedelta(hours=9)
    elapsed = (now_kst - start_time).total_seconds()

    if elapsed >= 600:  # 10분
        buffer_manager.flush_to_db()

    return {
        "status": "ok",
        "buffer_count": buffer_manager.buffer['risk_score_count'],
    }



@bp.route('/ingest', methods=['POST'])
def ingest():
    data = request.get_json()
    if not data: 
        return jsonify({"error": "No data"}), 400
    
    try:
        # [핵심] 무조건 서버의 현재 시간(UTC)을 기준으로 처리
        # (과거/미래 데이터가 들어와도 현재 발생한 것으로 간주)
        now = datetime.utcnow()
        now_kst = now + timedelta(hours=9)
        current_time = now_kst
        
        # 1. DB 저장을 위해 모델 생성
        val = float(data.get('value', 0.0))
        
        tx = RawTransaction(
            target_address=data.get('target_address'),
            risk_score=data.get('risk_score'),
            risk_level=str(data.get('risk_level', '')).lower(),
            chain_id=data.get('chain_id'),
            value=val,
            timestamp=current_time,  # DB에 "현재 시간"으로 저장
            raw_data=data 
        )
        db.session.add(tx)
        db.session.commit()

        # 2. 매니저에게 데이터 전달 (시간 정보는 Manager가 알아서 현재 시간으로 처리함)
        buffer_manager.add_data(data)

    except Exception as e:
        print(f"⚠️ Ingest Error: {e}")
        # 에러 나도 계속 진행

    # 버퍼 플러시 체크 (안전한 시간 계산)
    start_time = buffer_manager.buffer['start_time']
    # 타임존 정보가 있다면 제거 (에러 방지)
    if start_time.tzinfo is not None:
        start_time = start_time.replace(tzinfo=None)

    now = datetime.utcnow()   
    now_kst = now + timedelta(hours=9)
    elapsed = (now_kst - start_time).total_seconds()
    
    if elapsed >= 600: # 10분
        buffer_manager.flush_to_db()
        
    return jsonify({
        "status": "ok", 
        "buffer_count": buffer_manager.buffer['risk_score_count']
    }), 201

@bp.route('/dashboard', methods=['GET'])
def dashboard():
    now = datetime.utcnow()
    now_kst = now + timedelta(hours=9)
    update_dune_cache_if_needed()
    
    # 1년치 데이터 조회
    one_year_ago = now_kst - timedelta(days=370)
    aggregates = RiskAggregate.query.filter(RiskAggregate.timestamp >= one_year_ago).all()
    avg_temp_map = {k: {"sum": 0, "cnt": 0} for k in TIME_ORDER}
    today_start = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    for agg in aggregates:
        if today_start <= agg.timestamp <= now_kst:
            h = agg.timestamp.hour
            slot = f"{h - (h % 2):02}"
            if slot in avg_temp_map:
                avg_temp_map[slot]["sum"] += agg.total_risk_score
                avg_temp_map[slot]["cnt"] += agg.risk_score_count


    # 현재 버퍼에 있는 데이터도 실시간 반영
    curr_h = now_kst.hour
    curr_slot = f"{curr_h - (curr_h % 2):02}"
    if curr_slot in avg_temp_map:
        avg_temp_map[curr_slot]["sum"] += buffer_manager.buffer['risk_score_sum']
        avg_temp_map[curr_slot]["cnt"] += buffer_manager.buffer['risk_score_count']

    avg_risk_final = {}
    for k in TIME_ORDER:
        val = avg_temp_map[k]
        avg = round(val["sum"] / val["cnt"]) if val["cnt"] > 0 else 0
        avg_risk_final[k] = avg
    trend_keys = []
    for i in range(11, -1, -1):
        d = now_kst - relativedelta(months=i)
        trend_keys.append(d.strftime("%Y-%m"))
    trend_temp = {k: 0.0 for k in trend_keys}

    for agg in aggregates:
        k = agg.timestamp.strftime("%Y-%m")
        if k in trend_temp:
            trend_temp[k] += agg.high_risk_value_sum
            
    # 현재 월 버퍼 데이터 합산
    curr_month_key = now_kst.strftime("%Y-%m")
    if curr_month_key in trend_temp:
        trend_temp[curr_month_key] += buffer_manager.buffer.get('high_risk_value_sum', 0.0)
    
    trend_final = {k: round(v, 2) for k, v in trend_temp.items()}
    total_trend_value = sum(trend_final.values())
    chain_temp = {}
    for p_key in PERIOD_ORDER:
        chain_temp[p_key] = {c: 0 for c in TARGET_CHAINS}

    def get_period_key(dt):
        m = dt.month
        start = m - 1 if m % 2 == 0 else m
        return f"{start}~{start+1}월"

    def get_chain_name(raw_id_or_name):
        if raw_id_or_name in TARGET_CHAINS: return raw_id_or_name
        try: return CHAIN_ID_MAP.get(int(raw_id_or_name), "Others")
        except: return "Others"

    for agg in aggregates:
        if agg.timestamp.year == now_kst.year:
            p_key = get_period_key(agg.timestamp)
            if p_key in chain_temp and agg.chain_data:
                for raw_key, count in agg.chain_data.items():
                    name = get_chain_name(raw_key)
                    target = name if name in TARGET_CHAINS else "Others"
                    if target in chain_temp[p_key]: chain_temp[p_key][target] += count
    
    # 현재 버퍼 데이터 합산
    curr_p_key = get_period_key(now_kst)
    if curr_p_key in chain_temp:
        for raw_key, count in buffer_manager.buffer['chain_counts'].items():
            name = get_chain_name(raw_key)
            target = name if name in TARGET_CHAINS else "Others"
            if target in chain_temp[curr_p_key]: chain_temp[curr_p_key][target] += count

    # --- D. Top Cards (오늘의 경고/위험 건수) ---
    today_start = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    stats_today = db.session.query(
        func.sum(RiskAggregate.warning_tx_count),
        func.sum(RiskAggregate.high_risk_tx_count)
    ).filter(RiskAggregate.timestamp >= today_start).first()
    
    final_warning = (stats_today[0] or 0) + buffer_manager.buffer['warning_count']
    final_high = (stats_today[1] or 0) + buffer_manager.buffer['high_risk_count']
    response = {
        "data": {
            "totalVolume": DUNE_CACHE["data"]["totalVolume"],
            "totalTransactions": DUNE_CACHE["data"]["totalTransactions"],
            "highRiskTransactions": { "value": int(final_high), "changeRate": "+8.7%" },
            "warningTransactions": { "value": int(final_warning), "changeRate": "-2.3%" },
            "highRiskTransactionTrend": {
                "value": int(total_trend_value), 
                "trend": trend_final 
            },
            "highRiskTransactionsByChain": chain_temp,
            "averageRiskScore": avg_risk_final
        }
    }
    
    return jsonify(response)

@bp.route('/flush', methods=['POST'])
def force_flush():
    buffer_manager.flush_to_db()
    return jsonify({"status": "success", "message": "Flushed"}), 200
