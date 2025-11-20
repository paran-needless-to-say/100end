from dataclasses import dataclass
from src.types.node import Node
from src.types.edge import Edge
from src.utils.address_label import get_address_label

@dataclass
class Graph:
    def __init__(self):
        self.nodes: list[Node] = []
        self.edges: list[Edge] = []
    
    def to_dict(self):
        return {
            'nodes': [node.to_dict() for node in self.nodes],
            'edges': [edge.to_dict() for edge in self.edges]
        }
    
    def add_node(self, address: str, chain_id: int) -> None:
        if not address:
            return

        address = address.lower()
        node_id = f'{chain_id}-{address}'

        if node_id in [node.ID for node in self.nodes]:
            return

        # Get label from address_label.json if it exists
        label = get_address_label(chain_id=chain_id, address=address)

        self.nodes.append(Node(
            ID=node_id,
            ADDRESS=address,
            CHAIN_ID=chain_id,
            LABEL=label
        ))

    def add_edge(
            self,
            chain_id: int,
            tx_hash: str,
            block_height: int,
            from_address: str,
            to_address: str,
            amount: str,
            timestamp: int,
            token_address: str,
            token_symbol: str,
            usd_value: str,
            tx_type: str
        ) -> None:
        from_address = from_address.lower()
        to_address = to_address.lower()
        if token_address:
            token_address = token_address.lower()

        self.edges.append(Edge(
            CHAIN_ID=chain_id,
            TX_HASH=tx_hash,
            BLOCK_HEIGHT=block_height,
            FROM_ADDRESS=from_address,
            TO_ADDRESS=to_address,
            AMOUNT=amount,
            TIMESTAMP=timestamp,
            TOKEN_ADDRESS=token_address,
            TOKEN_SYMBOL=token_symbol,
            USD_VALUE=usd_value,
            TX_TYPE=tx_type
        ))