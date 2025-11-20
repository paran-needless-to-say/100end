import json
import os
from typing import Optional

_address_labels: Optional[dict] = None

def _load_address_labels() -> dict:
    """Load address labels from the JSON config file."""
    global _address_labels

    if _address_labels is not None:
        return _address_labels

    # Get the path to the config file
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
    """
    Get the label for a given address on a specific chain.

    Args:
        chain_id: The chain ID (e.g., 1 for Ethereum, 56 for BSC)
        address: The address to lookup (case-insensitive)

    Returns:
        The label string if found, None otherwise
    """
    labels = _load_address_labels()

    chain_id_str = str(chain_id)
    if chain_id_str not in labels:
        return None

    # Normalize address to lowercase for lookup
    address_lower = address.lower()

    # Check if address exists in the chain's labels
    chain_labels = labels[chain_id_str]

    # Try exact match first
    if address_lower in chain_labels:
        return chain_labels[address_lower]

    # Try checksummed version
    for addr_key, label in chain_labels.items():
        if addr_key.lower() == address_lower:
            return label

    return None


def reload_address_labels() -> None:
    """Force reload of address labels from the config file."""
    global _address_labels
    _address_labels = None
    _load_address_labels()
