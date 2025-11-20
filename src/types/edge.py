from dataclasses import dataclass


@dataclass
class Edge:
    CHAIN_ID: int
    TX_HASH: str
    BLOCK_HEIGHT: int
    FROM_ADDRESS: str
    TO_ADDRESS: str
    AMOUNT: str
    TIMESTAMP: int
    TOKEN_ADDRESS: str
    TOKEN_SYMBOL: str
    USD_VALUE: str
    TX_TYPE: str

    def to_dict(self):
        return {
            'chain_id': self.CHAIN_ID,
            'tx_hash': self.TX_HASH,
            'block_height': self.BLOCK_HEIGHT,
            'from_address': self.FROM_ADDRESS,
            'to_address': self.TO_ADDRESS,
            'amount': str(self.AMOUNT),
            'timestamp': self.TIMESTAMP,
            'token_address': self.TOKEN_ADDRESS,
            'token_symbol': self.TOKEN_SYMBOL,
            'usd_value': self.USD_VALUE,
            'tx_type': self.TX_TYPE
        }