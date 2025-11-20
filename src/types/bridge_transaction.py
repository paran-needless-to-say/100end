from dataclasses import dataclass

@dataclass
class BridgeTransaction:
    SRC_TX_HASH: str
    DST_TX_HASH: str
    SRC_CHAIN_ID: int
    DST_CHAIN_ID: int
    TOKEN_IN: str
    TOKEN_AMOUNT_IN: str
    TOKEN_OUT: str
    TOKEN_AMOUNT_OUT: str
    FROM: str
    TO: str
    TIMESTAMP: int
    
    def to_dict(self):
        return {
            'src_tx_hash': self.SRC_TX_HASH,
            'dst_tx_hash': self.DST_TX_HASH,
            'src_chain_id': self.SRC_CHAIN_ID,
            'dst_chain_id': self.DST_CHAIN_ID,
            'token_in': self.TOKEN_IN,
            'token_amount_int': self.TOKEN_AMOUNT_IN,
            'token_out': self.TOKEN_OUT,
            'token_amount_out': self.TOKEN_AMOUNT_OUT,
            'from': self.FROM,
            'to': self.TO,
            'timestamp': self.TIMESTAMP
        }