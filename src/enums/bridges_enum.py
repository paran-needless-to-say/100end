from dataclasses import dataclass

@dataclass(frozen=True)
class BridgesEnum:
    DEBRIDGE: str = 'DeBridge'
    RELAY: str = 'Relay'
    USDT0: str = 'USDT0'