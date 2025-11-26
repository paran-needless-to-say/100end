from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class RiskInfo:
    risk_score: int = 0
    risk_level: str = "low"
    risk_tags: List[str] = field(default_factory=list)
    fired_rules: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""
    completed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'risk_score': self.risk_score,
            'risk_level': self.risk_level,
            'risk_tags': self.risk_tags,
            'fired_rules': self.fired_rules,
            'explanation': self.explanation,
            'completed_at': self.completed_at
        }
