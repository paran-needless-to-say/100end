from dataclasses import dataclass

@dataclass(frozen=True)
class Txtype:
    NATIVE: str = "Native Transfer"
    ERC20: str = "ERC20 Transfer"
    BRIDGE: str = "Bridge"
