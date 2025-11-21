from typing import Dict, Any

from etherscan import Etherscan
from etherscan.enums.actions_enum import ActionsEnum as Actions

from src.enums.tx_types_enum import TxTypesEnum as TxTypes
from src.enums.methods_enum import MethodsEnum as Methods
from src.enums.bridges_enum import BridgesEnum as Bridges

from src.bridges import debridge, usdt0

from src.constants.bridge_methods import METHODS as BRIDGE_METHODS
from src.constants.swap_methods import METHODS as SWAP_METHODS
from src.constants.rpc_urls import URLS as RPC_URLS
from src.constants.token_addresses import USDT_ADDRESS
from src.types.graph import Graph
from src.types.scoring_graph import ScoringGraph

from web3 import Web3

NATIVE_TOKEN_DECIMALS = 18
DEFAULT_START_BLOCK = 0
DEFAULT_END_BLOCK = 99999999


class Analyzer:
    def __init__(self, api_key: str):
        self.scanner = Etherscan(api_key=api_key)

    def get_fund_flow_by_address(self, chain_id: int, address: str) -> Dict[str, Any]:
        graph = Graph()

        fetchers = [
            self._fetch_normal_txs,
            self._fetch_erc20_transfers
        ]

        for fetcher in fetchers:
            txs = fetcher(chain_id=chain_id, address=address)

            for tx in txs:
                self._add_nodes_from_tx(graph=graph, chain_id=chain_id, tx=tx)
                self._add_edge_from_tx(graph=graph, chain_id=chain_id, tx=tx)

        return graph.to_dict()

    def analyze_bridge_transaction(self, chain_id: int, tx_hash: str) -> Dict[str, Any]:
        url = RPC_URLS[str(chain_id)]
        w3 = Web3(Web3.HTTPProvider(url))

        result = w3.eth.get_transaction(transaction_hash=tx_hash)
        input_data = result['input']
        methodId = input_data[:10]

        bridge = BRIDGE_METHODS[methodId]['label']
        if bridge == 'DeBridge':
            dst_chain_id, recipient = debridge.decode_bridge_transaction(tx_hash=tx_hash)
        elif bridge == 'USDT0':
            dst_chain_id, recipient = usdt0.decode_bridge_transaction(tx_hash=tx_hash, chain_id=chain_id)
        else:
            raise NotImplementedError(f"Bridge protocol '{bridge}' not yet implemented")

        return self.get_fund_flow_by_address(chain_id=dst_chain_id, address=recipient)

    def get_multihop_fund_flow_for_scoring(
        self,
        chain_id: int,
        address: str,
        hop_count: int = 1
    ) -> Dict[str, Any]:
        graph = ScoringGraph()
        visited_addresses = set()

        main_address = address.lower()
        current_hop_addresses = {main_address}

        for hop in range(hop_count):
            next_hop_addresses = set()

            for current_address in current_hop_addresses:
                if current_address in visited_addresses:
                    continue

                visited_addresses.add(current_address)

                connected_addresses = self._get_fund_flow_for_scoring(
                    graph=graph,
                    chain_id=chain_id,
                    address=current_address
                )

                next_hop_addresses.update(connected_addresses)

            current_hop_addresses = next_hop_addresses

            if not current_hop_addresses:
                break

        return graph.to_dict()

    def _get_fund_flow_for_scoring(
        self,
        graph: ScoringGraph,
        chain_id: int,
        address: str
    ) -> set[str]:
        connected_addresses = set()
        address_lower = address.lower()

        try:
            normal_txs = self._fetch_normal_txs(chain_id=chain_id, address=address)

            for tx in normal_txs:
                from_addr = tx.get('from', '').lower()
                to_addr = tx.get('to', '').lower()

                self._add_nodes_from_tx_for_scoring(graph=graph, chain_id=chain_id, tx=tx)
                self._add_edge_from_tx_for_scoring(graph=graph, chain_id=chain_id, tx=tx)

                if to_addr == address_lower and from_addr:
                    connected_addresses.add(from_addr)
                if from_addr == address_lower and to_addr:
                    connected_addresses.add(to_addr)
        except Exception as e:
            print(f"Error fetching normal txs for {address}: {e}")

        try:
            erc20_txs = self._fetch_erc20_transfers(chain_id=chain_id, address=address)

            for tx in erc20_txs:
                from_addr = tx.get('from', '').lower()
                to_addr = tx.get('to', '').lower()

                self._add_nodes_from_tx_for_scoring(graph=graph, chain_id=chain_id, tx=tx)
                self._add_edge_from_tx_for_scoring(graph=graph, chain_id=chain_id, tx=tx)

                if to_addr == address_lower and from_addr:
                    connected_addresses.add(from_addr)
                if from_addr == address_lower and to_addr:
                    connected_addresses.add(to_addr)
        except Exception as e:
            print(f"Error fetching ERC20 txs for {address}: {e}")

        return connected_addresses

    def _add_nodes_from_tx_for_scoring(self, graph: ScoringGraph, chain_id: int, tx: Dict[str, Any]) -> None:
        from_address = tx['from']
        to_address = tx['to']

        for address in [from_address, to_address]:
            graph.add_node(address, chain_id)

    def _add_edge_from_tx_for_scoring(self, graph: ScoringGraph, chain_id: int, tx: Dict[str, Any]) -> None:
        token_symbol = tx.get('tokenSymbol')
        action = Actions.TOKENTX if token_symbol else Actions.TXLIST

        tx_type = self._classify_tx_type(tx=tx, action=action)
        if tx_type == TxTypes.UNKNOWN:
            return

        amount = int(tx['value'])
        token_address = ''
        block_height = int(tx['blockNumber'])
        usd_value = 0

        if tx_type == TxTypes.NATIVE:
            amount = str(amount / 10 ** NATIVE_TOKEN_DECIMALS)
            token_symbol = 'ETH'
        elif tx_type == TxTypes.ERC20_TRANSFER:
            decimals = int(tx['tokenDecimal'])
            amount = str(amount / 10 ** decimals)
            token_address = tx['contractAddress']
        elif tx_type in (TxTypes.BRIDGE, TxTypes.SWAP):
            amount = str(amount)

        graph.add_edge(
            chain_id=chain_id,
            tx_hash=tx['hash'],
            block_height=block_height,
            from_address=tx['from'],
            to_address=tx['to'],
            amount=amount,
            timestamp=tx['timeStamp'],
            token_address=token_address,
            token_symbol=token_symbol,
            usd_value=usd_value,
            tx_type=tx_type
        )

    def _add_nodes_from_tx(self, graph: Graph, chain_id: int, tx: Dict[str, Any]) -> None:
        from_address = tx['from']
        to_address = tx['to']

        for address in [from_address, to_address]:
            graph.add_node(address, chain_id)

    def _add_edge_from_tx(self, graph: Graph, chain_id: int, tx: Dict[str, Any]) -> None:
        token_symbol = tx.get('tokenSymbol')
        action = Actions.TOKENTX if token_symbol else Actions.TXLIST

        tx_type = self._classify_tx_type(tx=tx, action=action)
        if tx_type == TxTypes.UNKNOWN:
            return

        amount = int(tx['value'])
        token_address = ''
        block_height = int(tx['blockNumber'])
        usd_value = 0 # temp

        if tx_type == TxTypes.NATIVE:
            amount = str(amount / 10 ** NATIVE_TOKEN_DECIMALS)
            token_symbol = 'ETH'
        elif tx_type == TxTypes.ERC20_TRANSFER:
            decimals = int(tx['tokenDecimal'])
            amount = str(amount / 10 ** decimals)
            token_address = tx['contractAddress']
        elif tx_type in (TxTypes.BRIDGE, TxTypes.SWAP):
            amount = str(amount)

        graph.add_edge(
            chain_id=chain_id,
            tx_hash=tx['hash'],
            block_height=block_height,
            from_address=tx['from'],
            to_address=tx['to'],
            amount=amount,
            timestamp=tx['timeStamp'],
            token_address=token_address,
            token_symbol=token_symbol,
            usd_value=usd_value,
            tx_type=tx_type
        )

    def _fetch_normal_txs(self, chain_id: int, address: str) -> list:
        return self.scanner.get_normal_txs_by_address(
            address=address,
            startblock=DEFAULT_START_BLOCK,
            endblock=DEFAULT_END_BLOCK,
            sort='desc',
            chain_id=chain_id
        )

    def _fetch_erc20_transfers(self, chain_id: int, address: str) -> list:
        return self.scanner.get_erc20_token_transfer_events_by_address(
            address=address,
            startblock=DEFAULT_START_BLOCK,
            endblock=DEFAULT_END_BLOCK,
            sort='desc',
            chain_id=chain_id
        )

    def _classify_tx_type(self, tx: Dict[str, Any], action: str) -> str:
        input_data = tx['input']
        method_id = tx['methodId']

        if action == Actions.TOKENTX:
            if method_id == Methods.ERC20_TRANSFER:
                return TxTypes.ERC20_TRANSFER

        elif action == Actions.TXLIST:
            if input_data == '0x':
                return TxTypes.NATIVE

        if method_id in SWAP_METHODS:
            return TxTypes.SWAP
        elif method_id in BRIDGE_METHODS:
            return TxTypes.BRIDGE

        return TxTypes.UNKNOWN