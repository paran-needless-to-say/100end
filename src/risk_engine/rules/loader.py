from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional
import yaml

class RuleLoader:
    
    def __init__(self, rules_path: str = "rules/tracex_rules.yaml"):
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

