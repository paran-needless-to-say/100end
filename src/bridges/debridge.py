import requests
from typing import Tuple
from src.constants.chain_id_mapping import convert_debridge_to_etherscan_chain_id

API_URL = 'https://stats-api.dln.trade/api/Orders/'
STRING_VALUE = 'stringValue'

def get_order_id_by_tx_hash(tx_hash: str) -> str:
    data = {
        'giveChainIds': [],
        'takeChainIds': [],
        'filter': f'{tx_hash}',
        'skip': 0,
        'take': 25
    }

    response = requests.post(API_URL + 'filteredList', json=data)
    result = response.json()

    order = result.get('orders', [])[0]
    order_id = order.get('orderId').get('stringValue')

    return order_id

def decode_bridge_transaction(tx_hash: str) -> Tuple[int, str]:
    order_id = get_order_id_by_tx_hash(tx_hash)

    response = requests.get(API_URL + order_id)
    result = response.json()

    dst_chain_id_debridge = result['takeOfferWithMetadata']['chainId'][STRING_VALUE]
    dst_chain_id = convert_debridge_to_etherscan_chain_id(dst_chain_id_debridge)
    recipient = result['receiverDst'][STRING_VALUE]

    return dst_chain_id, recipient

if __name__ == '__main__':
    tx_hash = '0x9155d2fd709b5d5b4f190ea8299e260a0d7c32a69925a10830b2e02c3728b8b1'
    print(decode_bridge_transaction(tx_hash))