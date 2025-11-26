from __future__ import annotations

from pathlib import Path
from typing import Dict, Set, Optional
import json

class ListLoader:
    
    def __init__(self, data_dir: str = "data/lists"):
        self.data_dir = Path(data_dir)
        self._cache: Dict[str, Set[str]] = {}
    
    def get_sdn_list(self) -> Set[str]:
        if "SDN_LIST" not in self._cache:
            self._cache["SDN_LIST"] = self._load_json_list("sdn_addresses.json")
        return self._cache["SDN_LIST"]
    
    def get_cex_list(self) -> Set[str]:
        if "CEX_LIST" not in self._cache:
            self._cache["CEX_LIST"] = self._load_cex_list()
        return self._cache["CEX_LIST"]
    
    def get_mixer_list(self) -> Set[str]:
        if "MIXER_LIST" not in self._cache:
            self._cache["MIXER_LIST"] = self._load_mixer_list()
        return self._cache["MIXER_LIST"]
    
    def get_bridge_list(self) -> Set[str]:
        if "BRIDGE_LIST" not in self._cache:
            self._cache["BRIDGE_LIST"] = self._load_bridge_list()
        return self._cache["BRIDGE_LIST"]
    
    def get_scam_list(self) -> Set[str]:
        if "SCAM_LIST" not in self._cache:
            self._cache["SCAM_LIST"] = self._load_json_list("scam_addresses.json")
        return self._cache["SCAM_LIST"]
    
    def get_all_lists(self) -> Dict[str, Set[str]]:
        return {
            "SDN_LIST": self.get_sdn_list(),
            "CEX_LIST": self.get_cex_list(),
            "MIXER_LIST": self.get_mixer_list(),
            "BRIDGE_LIST": self.get_bridge_list(),
            "SCAM_LIST": self.get_scam_list(),
        }
    
    def _load_json_list(self, filename: str) -> Set[str]:
        file_path = self.data_dir / filename
        if not file_path.exists():
            legacy_path = Path("dataset") / filename
            if legacy_path.exists():
                file_path = legacy_path
            else:
                return set()
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {addr.lower() for addr in data}
                elif isinstance(data, dict):
                    addresses = data.get("addresses", [])
                    return {addr.lower() for addr in addresses}
                return set()
        except Exception:
            return set()
    
    def _load_cex_list(self) -> Set[str]:
        file_path = self.data_dir / "cex_addresses.json"
        if not file_path.exists():
            legacy_path = Path("dataset") / "cex_addresses.json"
            if legacy_path.exists():
                file_path = legacy_path
            else:
                return set()
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                addresses = set()
                if isinstance(data, dict):
                    for cex_name, addr_list in data.items():
                        if isinstance(addr_list, list):
                            addresses.update(addr.lower() for addr in addr_list)
                return addresses
        except Exception:
            return set()
    
    def _load_mixer_list(self) -> Set[str]:
        file_path = self.data_dir / "bridge_contracts.json"
        if not file_path.exists():
            legacy_path = Path("dataset") / "bridge_contracts.json"
            if legacy_path.exists():
                file_path = legacy_path
            else:
                return set()
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                mixer_services = data.get("mixer_services", [])
                return {addr.lower() for addr in mixer_services}
        except Exception:
            return set()
    
    def _load_bridge_list(self) -> Set[str]:
        file_path = self.data_dir / "bridge_contracts.json"
        if not file_path.exists():
            legacy_path = Path("dataset") / "bridge_contracts.json"
            if legacy_path.exists():
                file_path = legacy_path
            else:
                return set()
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                bridges = data.get("bridges", [])
                addresses = set()
                for bridge in bridges:
                    contracts = bridge.get("contracts", {})
                    for chain, addr in contracts.items():
                        if addr:
                            addresses.add(addr.lower())
                return addresses
        except Exception:
            return set()

