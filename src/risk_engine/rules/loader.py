from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import os

class RuleLoader:

    def __init__(self, rules_path: str = None):
        if rules_path is None:
            # 현재 파일 위치 기준으로 tracex_rules.yaml 찾기
            current_dir = Path(__file__).parent
            rules_path = current_dir / "tracex_rules.yaml"
        self.rules_path = Path(rules_path)
        self._ruleset: Optional[Dict[str, Any]] = None
    
    def load(self) -> Dict[str, Any]:
        if self._ruleset is None:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                self._ruleset = yaml.safe_load(f)
        return self._ruleset
    
    def get_rules(self) -> list:
        ruleset = self.load()
        return ruleset.get("rules", [])
    
    def get_defaults(self) -> Dict[str, Any]:
        ruleset = self.load()
        return ruleset.get("defaults", {})

