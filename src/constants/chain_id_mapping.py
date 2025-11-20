DEBRIDGE_TO_ETHERSCAN_CHAIN_ID = {
    '42161': 42161,
    '43114': 43114,
    '56': 56,
    '1': 1,
    '137': 137,
    '59144': 59144,
    '8453': 8453,
    '10': 10,
    '100000001': None,
    '100000002': 100,
    '100000003': None,
    '100000004': None,
    '100000005': None,
    '100000014': 146,
    '100000006': None,
    '100000010': None,
    '100000017': 2741,
    '100000020': 80094,
    '100000013': None,
    '100000022': 999,
    '100000015': None,
    '100000009': None,
    '100000008': None,
    '100000021': None,
    '100000023': 5000,
    '100000024': None,
    '100000025': 50104,
    '100000027': 1329,
    '100000026': None,
    '7565164': None,
}

def convert_debridge_to_etherscan_chain_id(debridge_chain_id: str) -> int:
    chain_id = DEBRIDGE_TO_ETHERSCAN_CHAIN_ID.get(str(debridge_chain_id))
    if chain_id is None:
        raise ValueError(f"Chain ID {debridge_chain_id} not supported by Etherscan")
    return chain_id
