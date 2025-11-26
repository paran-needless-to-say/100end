from __future__ import annotations

import requests
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

class EtherscanClient:
    
    BASE_URL = "https://api.etherscan.io/v2/api"
    
    CHAIN_IDS = {
        "ethereum": 1,
        "bsc": 56,
        "polygon": 137,
    }
    
    def __init__(self, api_key: Optional[str] = None, chain: str = "ethereum"):
        self.chain = chain.lower()
        self.chain_id = self.CHAIN_IDS.get(self.chain)
        if not self.chain_id:
            raise ValueError(f"Unsupported chain: {chain}. Supported: {list(self.CHAIN_IDS.keys())}")
        
        self.base_url = self.BASE_URL
        
        self.api_key = api_key or os.getenv("ETHERSCAN_API_KEY", "91FZVKNIX7GYPESECU5PHPZIMKD72REX43")
        if not self.api_key:
            print("Warning: ETHERSCAN_API_KEY not set. Some API calls may fail.")
    
    def get_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 10000,
        sort: str = "asc"
    ) -> List[Dict[str, Any]]:
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": min(offset, 10000),  # 최대 10000
            "sort": sort,
            "apikey": self.api_key
        }
        
        response = self._make_request(params)
        
        if response.get("status") == "1" and response.get("message") == "OK":
            return response.get("result", [])
        elif response.get("message") == "No transactions found":
            return []
        else:
            raise Exception(f"API Error: {response.get('message', 'Unknown error')}")
    
    def get_internal_transactions(
        self,
        address: str,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 10000,
        sort: str = "asc"
    ) -> List[Dict[str, Any]]:
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "account",
            "action": "txlistinternal",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": min(offset, 10000),
            "sort": sort,
            "apikey": self.api_key
        }
        
        response = self._make_request(params)
        
        if response.get("status") == "1" and response.get("message") == "OK":
            return response.get("result", [])
        elif response.get("message") == "No transactions found":
            return []
        else:
            raise Exception(f"API Error: {response.get('message', 'Unknown error')}")
    
    def get_token_transfers(
        self,
        address: str,
        contract_address: Optional[str] = None,
        start_block: int = 0,
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 10000,
        sort: str = "asc"
    ) -> List[Dict[str, Any]]:
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": min(offset, 10000),
            "sort": sort,
            "apikey": self.api_key
        }
        
        if contract_address:
            params["contractaddress"] = contract_address
        
        response = self._make_request(params)
        
        if response.get("status") == "1" and response.get("message") == "OK":
            return response.get("result", [])
        elif response.get("message") == "No transactions found":
            return []
        else:
            raise Exception(f"API Error: {response.get('message', 'Unknown error')}")
    
    def get_balance(self, address: str) -> str:
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": self.api_key
        }
        
        response = self._make_request(params)
        
        if response.get("status") == "1":
            return response.get("result", "0")
        else:
            raise Exception(f"API Error: {response.get('message', 'Unknown error')}")
    
    def get_contract_info(self, address: str) -> Dict[str, Any]:
        params = {
            "chainid": self.chain_id,  # V2: chainid 추가
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
            "apikey": self.api_key
        }
        
        response = self._make_request(params)
        
        if response.get("status") == "1":
            result = response.get("result", [{}])[0] if response.get("result") else {}
            source_code = result.get("SourceCode", "")
            
            return {
                "is_contract": bool(source_code),
                "contract_name": result.get("ContractName", ""),
                "compiler_version": result.get("CompilerVersion", ""),
                "is_token": "token" in result.get("ContractName", "").lower() or 
                           "erc20" in source_code.lower() or
                           "erc721" in source_code.lower()
            }
        else:
            return {
                "is_contract": False,
                "contract_name": "",
                "compiler_version": "",
                "is_token": False
            }
    
    def get_address_tags(self, address: str) -> Dict[str, Any]:
        tags = {
            "label": "unknown",
            "entity_type": "unknown",
            "is_contract": False,
            "is_token": False,
            "is_exchange": False,
            "is_mixer": False,
            "is_bridge": False
        }
        
        contract_info = self.get_contract_info(address)
        tags["is_contract"] = contract_info.get("is_contract", False)
        tags["is_token"] = contract_info.get("is_token", False)
        
        if tags["is_token"]:
            tags["label"] = "token"
            tags["entity_type"] = "token"
        elif tags["is_contract"]:
            tags["label"] = "contract"
            tags["entity_type"] = "contract"
        
        from src.risk_engine.data.lists import ListLoader
        list_loader = ListLoader()
        
        cex_list = list_loader.get_cex_list()
        mixer_list = list_loader.get_mixer_list()
        bridge_list = list_loader.get_bridge_list()
        
        addr_lower = address.lower()
        
        if addr_lower in mixer_list:
            tags["is_mixer"] = True
            tags["label"] = "mixer"
            tags["entity_type"] = "mixer"
        elif addr_lower in cex_list:
            tags["is_exchange"] = True
            tags["label"] = "cex"
            tags["entity_type"] = "cex"
        elif addr_lower in bridge_list:
            tags["is_bridge"] = True
            tags["label"] = "bridge"
            tags["entity_type"] = "bridge"
        
        contract_name = contract_info.get("contract_name", "").lower()
        if "exchange" in contract_name or "swap" in contract_name:
            tags["is_exchange"] = True
            if tags["label"] == "unknown":
                tags["label"] = "dex"
                tags["entity_type"] = "dex"
        
        return tags
    
    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        time.sleep(0.2)
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get("status") == "0" and result.get("message") != "No transactions found":
                error_msg = result.get("message", "Unknown error")
                error_result = result.get("result", "")
                print(f"  ⚠️  Etherscan API Warning: {error_msg}")
                if error_result:
                    print(f"     Details: {error_result}")
            
            return result
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")
    
    def normalize_transaction(self, tx: Dict[str, Any], chain: str = "ethereum") -> Dict[str, Any]:
        timestamp = int(tx.get("timeStamp", 0))
        timestamp_iso = datetime.fromtimestamp(timestamp).isoformat() + "Z" if timestamp else ""
        
        value_wei = int(tx.get("value", 0))
        value_eth = value_wei / 1e18
        
        
        return {
            "tx_hash": tx.get("hash", ""),
            "from": tx.get("from", ""),
            "to": tx.get("to", ""),
            "timestamp": timestamp_iso,
            "block_height": int(tx.get("blockNumber", 0)),
            "value_wei": value_wei,
            "value_eth": value_eth,
            "amount_usd": 0.0,  # 시세 API로 변환 필요
            "gas_used": int(tx.get("gasUsed", 0)),
            "gas_price": int(tx.get("gasPrice", 0)),
            "chain": chain,
            "asset_contract": "0xETH",  # Native token
            "is_error": tx.get("isError", "0") == "1",
            "tx_receipt_status": tx.get("txreceipt_status", "1") == "1"
        }

class RealDataCollector:
    
    def __init__(self, api_key: Optional[str] = None, chain: str = "ethereum"):
        self.client = EtherscanClient(api_key=api_key, chain=chain)
        self.chain = chain
    
    def collect_address_transactions(
        self,
        address: str,
        max_transactions: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        all_transactions = []
        page = 1
        offset = 10000
        
        while True:
            try:
                txs = self.client.get_transactions(
                    address=address,
                    page=page,
                    offset=offset,
                    sort="desc"  # 최신순
                )
                
                if not txs:
                    break
                
                normalized = [
                    self.client.normalize_transaction(tx, self.chain)
                    for tx in txs
                ]
                
                all_transactions.extend(normalized)
                
                if max_transactions and len(all_transactions) >= max_transactions:
                    all_transactions = all_transactions[:max_transactions]
                    break
                
                if len(txs) < offset:
                    break
                
                page += 1
                
                time.sleep(0.2)
                
            except Exception as e:
                print(f"Error collecting transactions: {e}")
                break
        
        return all_transactions
    
    def collect_high_risk_addresses(
        self,
        addresses: List[str],
        max_transactions_per_address: int = 100
    ) -> List[Dict[str, Any]]:
        all_transactions = []
        
        for i, address in enumerate(addresses):
            print(f"Collecting {i+1}/{len(addresses)}: {address}")
            
            try:
                txs = self.collect_address_transactions(
                    address=address,
                    max_transactions=max_transactions_per_address
                )
                all_transactions.extend(txs)
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Error collecting from {address}: {e}")
                continue
        
        return all_transactions

if __name__ == "__main__":
    API_KEY = os.getenv("ETHERSCAN_API_KEY", "YOUR_API_KEY_HERE")
    
    collector = RealDataCollector(api_key=API_KEY, chain="ethereum")
    
    address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"  # 예시 주소
    transactions = collector.collect_address_transactions(
        address=address,
        max_transactions=100
    )
    
    print(f"수집된 거래 수: {len(transactions)}")
    if transactions:
        print(f"첫 거래: {transactions[0]}")

