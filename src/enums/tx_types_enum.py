from dataclasses import dataclass

@dataclass(frozen=True)
class TxTypesEnum:
    ERC20_TRANSFER: str = 'ERC20_Transfer'
    UNKNOWN: str = 'Unknown'
    BRIDGE: str = 'Bridge'
    NATIVE: str = 'Native'
    SWAP: str = 'Swap'