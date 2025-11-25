"""
의심거래 보고서 관련 API
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 보고서 저장 디렉토리 (로컬 파일 시스템 사용)
REPORTS_DIR = Path(__file__).parent.parent.parent / "data" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

REPORTS_FILE = REPORTS_DIR / "suspicious_reports.json"


def load_reports() -> List[Dict[str, Any]]:
    """저장된 보고서 목록 로드"""
    if not REPORTS_FILE.exists():
        return []
    
    try:
        with open(REPORTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading reports: {e}")
        return []


def save_reports(reports: List[Dict[str, Any]]) -> None:
    """보고서 목록 저장"""
    try:
        with open(REPORTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(reports, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving reports: {e}")
        raise


def create_report(
    title: str,
    address: str,
    chain_id: int,
    risk_score: float,
    risk_level: str,
    description: str,
    analysis_data: Optional[Dict[str, Any]] = None,
    transaction_hashes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """새 보고서 생성"""
    reports = load_reports()
    
    # 새 보고서 ID 생성
    report_id = len(reports) + 1
    
    report = {
        "id": report_id,
        "title": title,
        "address": address.lower(),
        "chain_id": chain_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "description": description,
        "analysis_data": analysis_data or {},
        "transaction_hashes": transaction_hashes or [],
        "status": "pending",  # pending, reviewed, resolved
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    reports.append(report)
    save_reports(reports)
    
    return report


def get_report(report_id: int) -> Optional[Dict[str, Any]]:
    """특정 보고서 조회"""
    reports = load_reports()
    for report in reports:
        if report["id"] == report_id:
            return report
    return None


def get_all_reports(
    status: Optional[str] = None,
    chain_id: Optional[int] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """보고서 목록 조회 (필터링 지원)"""
    reports = load_reports()
    
    # 필터링
    filtered = reports
    if status:
        filtered = [r for r in filtered if r.get("status") == status]
    if chain_id:
        filtered = [r for r in filtered if r.get("chain_id") == chain_id]
    
    # 최신순 정렬
    filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # 제한
    return filtered[:limit]


def update_report_status(report_id: int, status: str) -> Optional[Dict[str, Any]]:
    """보고서 상태 업데이트"""
    reports = load_reports()
    
    for report in reports:
        if report["id"] == report_id:
            report["status"] = status
            report["updated_at"] = datetime.now().isoformat()
            save_reports(reports)
            return report
    
    return None

