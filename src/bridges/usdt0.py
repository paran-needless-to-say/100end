import requests
import eth_abi
from typing import Tuple
from web3 import Web3
from src.constants.rpc_urls import URLS as RPC_URLS
from src.constants.chain_id_mapping import convert_layerzero_to_etherscan_chain_id

METADATA_API_URL = 'https://metadata.layerzero-api.com/v1/metadata/deployments'

def _get_chain_name_by_endpoint_id(endpoint_id: int) -> str:
    response = requests.get(METADATA_API_URL)
    data = response.json()

    for value in data.values():
        deployments = value.get('deployments')

        if deployments is None:
            continue

        for deployment in deployments:
            if int(deployment.get('eid')) == endpoint_id:
                return deployment.get('chainKey')

    return None

def decode_bridge_transaction(tx_hash: str, chain_id: int) -> Tuple[int, str]:
    url = RPC_URLS[str(chain_id)]
    w3 = Web3(Web3.HTTPProvider(url))

    tx = w3.eth.get_transaction(transaction_hash=tx_hash)

    input_data = tx['input']
    raw_data = bytes.fromhex(input_data[10:])

    parameters = [
        '(uint32,bytes32,uint256,uint256,bytes,bytes,bytes)',
        '(uint256,uint256)',
        'address'
    ]

    decoded = eth_abi.decode(parameters, raw_data)

    dest_endpoint_id, recipient, _, _, _, _, _ = decoded[0]
    dest_chain_key = _get_chain_name_by_endpoint_id(dest_endpoint_id)
    dest_chain_id = convert_layerzero_to_etherscan_chain_id(dest_chain_key)
    recipient = '0x' + recipient.hex()[24:]

    return dest_chain_id, recipient

if __name__ == '__main__':
    tx_hash = '0x5acae7c5f84f168a992c9d3e9debc1c32be2e8a7606e2cdeef82059f574bf748'
    chain_id = 1
    print(decode_bridge_transaction(tx_hash, chain_id))
