from flask import jsonify, request
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from collections import defaultdict
from ..extensions import db
from .models import RawTransaction, RiskAggregate
from .manager import buffer_manager
from . import bp

from .extract_transaction_and_amount import get_total_data

DUNE_CACHE = {
    "last_updated": None,
    "data": {
        "totalVolume": {"value": 0, "changeRate": "0%"},
        "totalTransactions": {"value": 0, "changeRate": "0%"}
    }
}

def update_dune_cache_if_needed():
    global DUNE_CACHE
    now = datetime.now()
    
    if DUNE_CACHE["last_updated"] and (now - DUNE_CACHE["last_updated"]).total_seconds() < 300:
        return

    print("⏳ Dune 데이터 갱신 중... (Volume/Tx만 조회)")
    
    total_data = get_total_data()
    
    DUNE_CACHE["data"]["totalVolume"] = total_data.get("totalVolume", {"value":0, "changeRate":"0%"})
    DUNE_CACHE["data"]["totalTransactions"] = total_data.get("totalTransactions", {"value":0, "changeRate":"0%"})
    
    DUNE_CACHE["last_updated"] = now
    print("✅ Dune 데이터 갱신 완료!")

TARGET_CHAINS = ["Ethereum", "Bitcoin", "Base", "Others"]
CHAIN_ID_MAP = { 1: "Ethereum", 0: "Bitcoin", 8453: "Base" }
PERIOD_ORDER = ["1~2월", "3~4월", "5~6월", "7~8월", "9~10월", "11~12월"]
TIME_ORDER = [f"{i:02}" for i in range(0, 24, 2)]

def parse_time(ts):
    if not ts: return datetime.utcnow()
    try: return datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
    except: return datetime.utcnow()

@bp.route('/ingest', methods=['POST'])
def ingest():
    data = request.get_json()
    if not data: return jsonify({"error": "No data"}), 400
    
    try:
        if 'data' not in data or not data['data'].get('nodes'):
             return jsonify({"error": "Invalid JSON structure"}), 400
             
        node = data['data']['nodes'][0]
        risk = node.get('risk', {})
        val = float(risk.get("amount_usd", 0.0) or 0.0)
        
        time_val = risk.get('completed_at') or risk.get('timestamp')
        final_time = parse_time(time_val)
        
        tx = RawTransaction(
            target_address=node.get('address'),
            risk_score=risk.get('risk_score'),
            risk_level=str(risk.get('risk_level', '')).lower(),
            chain_id=node.get('chain_id'),
            value=val,
            timestamp=final_time,
            raw_data=data 
        )
        db.session.add(tx)
        db.session.commit()
    except Exception as e:
        print(f"DB Error: {e}")

    buffer_manager.add_data(data)
    
    elapsed = (datetime.utcnow() - buffer_manager.buffer['start_time']).total_seconds()
    if elapsed >= 600:
        buffer_manager.flush_to_db()
        
    return jsonify({"status": "ok", "current_buffer": buffer_manager.buffer['risk_score_count']}), 201

@bp.route('/dashboard', methods=['GET'])
def dashboard():
    now = datetime.utcnow()
    update_dune_cache_if_needed()
    
    one_year_ago = now - timedelta(days=370)
    aggregates = RiskAggregate.query.filter(RiskAggregate.timestamp >= one_year_ago).all()

    avg_temp_map = {k: {"sum": 0, "cnt": 0} for k in TIME_ORDER}
    cutoff_24h = now - timedelta(hours=24)
    for agg in aggregates:
        if agg.timestamp >= cutoff_24h:
            h = agg.timestamp.hour
            slot = f"{h - (h % 2):02}"
            if slot in avg_temp_map:
                avg_temp_map[slot]["sum"] += agg.total_risk_score
                avg_temp_map[slot]["cnt"] += agg.risk_score_count
    
    curr_h = now.hour
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
        d = now - relativedelta(months=i)
        trend_keys.append(d.strftime("%Y-%m"))
    trend_temp = {k: 0.0 for k in trend_keys}

    for agg in aggregates:
        k = agg.timestamp.strftime("%Y-%m")
        if k in trend_temp:
            trend_temp[k] += agg.high_risk_value_sum
            
    curr_month_key = now.strftime("%Y-%m")
    if curr_month_key in trend_temp:
        trend_temp[curr_month_key] += buffer_manager.buffer.get('high_risk_value_sum', 0.0)
    
    trend_final = {k: round(v, 2) for k, v in trend_temp.items()}
    total_trend_value = sum(trend_final.values())
    trend_response_object = {
        "value": int(total_trend_value), 
        "trend": trend_final             
    }

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
        if agg.timestamp.year == now.year:
            p_key = get_period_key(agg.timestamp)
            if p_key in chain_temp and agg.chain_data:
                for raw_key, count in agg.chain_data.items():
                    name = get_chain_name(raw_key)
                    target = name if name in TARGET_CHAINS else "Others"
                    if target in chain_temp[p_key]: chain_temp[p_key][target] += count
    
    curr_p_key = get_period_key(now)
    if curr_p_key in chain_temp:
        for raw_key, count in buffer_manager.buffer['chain_counts'].items():
            name = get_chain_name(raw_key)
            target = name if name in TARGET_CHAINS else "Others"
            if target in chain_temp[curr_p_key]: chain_temp[curr_p_key][target] += count
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
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
            "highRiskTransactions": { "value": int(final_high), "changeRate": "0.0%" },
            "warningTransactions": { "value": int(final_warning), "changeRate": "0.0%" },
            "highRiskTransactionTrend": trend_response_object,
            "highRiskTransactionsByChain": chain_temp,
            "averageRiskScore": avg_risk_final
        }
    }
    
    return jsonify(response)

@bp.route('/flush', methods=['POST'])
def force_flush():
    if buffer_manager.buffer['risk_score_count'] == 0:
        return jsonify({"status": "ignored", "message": "Buffer empty"}), 200
    buffer_manager.flush_to_db()
    return jsonify({"status": "success", "message": "Flushed"}), 200
