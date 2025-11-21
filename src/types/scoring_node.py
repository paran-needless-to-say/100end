from dataclasses import dataclass
from typing import Optional


@dataclass
class ScoringNode:
    ID: str
    ADDRESS: str
    CHAIN_ID: int
    LABEL: Optional[str] = None
    IS_BRIDGE: bool = False
    IS_KNOWN_SCAM: bool = False
    IS_MIXER: bool = False
    IS_SANCTIONED: bool = False

    def to_dict(self):
        return {
            'id': self.ID,
            'address': self.ADDRESS,
            'chain_id': self.CHAIN_ID,
            'label': self.LABEL,
            'is_bridge': self.IS_BRIDGE,
            'is_known_scam': self.IS_KNOWN_SCAM,
            'is_mixer': self.IS_MIXER,
            'is_sanctioned': self.IS_SANCTIONED
        }
