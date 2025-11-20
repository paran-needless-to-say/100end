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