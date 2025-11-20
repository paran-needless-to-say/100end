import requests
from src.types.bridge_transaction import BridgeTransaction

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

def decode_bridge_transaction(tx_hash: str) -> BridgeTransaction:
    order_id = get_order_id_by_tx_hash(tx_hash)

    response = requests.get(API_URL + order_id)
    result = response.json()

    token_amount_wei_in = result['preswapData']['inAmount']['bigIntegerValue']
    token_decimals_in = result['preswapData']['tokenInMetadata']['decimals']

    token_amount_wei_out = result['takeOfferWithMetadata']['finalAmount']['bigIntegerValue']
    token_decimals_out = result['takeOfferWithMetadata']['decimals']

    return BridgeTransaction(
        SRC_TX_HASH=result['createdSrcEventMetadata']['transactionHash'][STRING_VALUE],
        DST_TX_HASH=result['fulfilledDstEventMetadata']['transactionHash'][STRING_VALUE],
        SRC_CHAIN_ID=result['giveOfferWithMetadata']['chainId'][STRING_VALUE],
        DST_CHAIN_ID=result['takeOfferWithMetadata']['chainId'][STRING_VALUE],
        TOKEN_IN=result['preswapData']['tokenInMetadata']['symbol'],
        TOKEN_AMOUNT_IN=str(token_amount_wei_in / 10 ** token_decimals_in),
        TOKEN_OUT=result['takeOfferWithMetadata']['symbol'],
        TOKEN_AMOUNT_OUT=str(token_amount_wei_out / 10 ** token_decimals_out),
        FROM=result['makerSrc'][STRING_VALUE],
        TO=result['receiverDst'][STRING_VALUE],
        TIMESTAMP=result['createdSrcEventMetadata']['blockTimeStamp']
    )

if __name__ == '__main__':
    tx_hash = '0x9155d2fd709b5d5b4f190ea8299e260a0d7c32a69925a10830b2e02c3728b8b1'
    print(decode_bridge_transaction(tx_hash))