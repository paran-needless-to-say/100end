from dataclasses import dataclass, field
from typing import Optional

from src.types.risk_info import RiskInfo

@dataclass
class Node:
    ID: str
    ADDRESS: str
    CHAIN_ID: int
    LABEL: Optional[str] = None
    IS_CONTRACT: bool = False
    RISK: RiskInfo = field(default_factory=RiskInfo)

    def to_dict(self):
        return {
            'id': self.ID,
            'address': self.ADDRESS,
            'chain_id': self.CHAIN_ID,
            'label': self.LABEL,
            'is_contract': self.IS_CONTRACT,
            'risk': self.RISK.to_dict()
        }
