from dataclasses import dataclass

@dataclass(frozen=True)
class RpcEnum:
    BNB: str = 'https://1rpc.io/bnb'
    BASE: str = 'https://1rpc.io/base'
    PLASMA: str = 'https://plasma.drpc.org'
    POLYGON: str = 'https://1rpc.io/matic'
    ETHEREUM: str = 'https://1rpc.io/eth'
    ARBITRUM: str = 'https://1rpc.io/arb'