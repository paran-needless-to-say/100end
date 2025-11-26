import json
import os
from typing import Optional

_address_labels: Optional[dict] = None

def _load_address_labels() -> dict:
    global _address_labels

    if _address_labels is not None:
        return _address_labels

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, '..', 'configs', 'address_label.json')

    try:
        with open(config_path, 'r') as f:
            _address_labels = json.load(f)
        return _address_labels
    except FileNotFoundError:
        print(f"Warning: address_label.json not found at {config_path}")
        _address_labels = {}
        return _address_labels
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse address_label.json: {e}")
        _address_labels = {}
        return _address_labels

def get_address_label(chain_id: int, address: str) -> Optional[str]:
    labels = _load_address_labels()

    chain_id_str = str(chain_id)
    if chain_id_str not in labels:
        return None

    address_lower = address.lower()

    chain_labels = labels[chain_id_str]

    if address_lower in chain_labels:
        return chain_labels[address_lower]

    for addr_key, label in chain_labels.items():
        if addr_key.lower() == address_lower:
            return label

    return None

def reload_address_labels() -> None:
    global _address_labels
    _address_labels = None
    _load_address_labels()
