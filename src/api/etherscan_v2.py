"""
Etherscan V2 API Client
"""
import requests
from typing import Dict, Any, List


class EtherscanV2Client:
    """Etherscan V2 API Client"""
    
    BASE_URL = "https://api.etherscan.io/v2/api"
    
    def __init__(self, api_key: str, chain_id: int = 1):
        self.api_key = api_key
        self.chain_id = chain_id  # Default: 1 (Ethereum Mainnet)
        self.session = requests.Session()
    
    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request to Etherscan V2"""
        params['apikey'] = self.api_key
        params['chainid'] = self.chain_id  # V2 requires chainid parameter
        
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '0' and data.get('message') == 'NOTOK':
                raise Exception(f"Etherscan API Error: {data.get('result', 'Unknown error')}")
            
            return data
        except requests.exceptions.RequestException as e:
            raise Exception(f"Etherscan API request failed: {str(e)}")
    
    def get_normal_transactions(
        self,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """Get normal transactions for an address"""
        params = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': startblock,
            'endblock': endblock,
            'page': page,
            'offset': offset,
            'sort': sort
        }
        
        result = self._make_request(params)
        return result.get('result', [])
    
    def get_erc20_transfers(
        self,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = 'desc',
        contractaddress: str = None
    ) -> List[Dict[str, Any]]:
        """Get ERC20 token transfers for an address"""
        params = {
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': startblock,
            'endblock': endblock,
            'page': page,
            'offset': offset,
            'sort': sort
        }
        
        if contractaddress:
            params['contractaddress'] = contractaddress
        
        result = self._make_request(params)
        return result.get('result', [])
    
    def get_internal_transactions(
        self,
        address: str,
        startblock: int = 0,
        endblock: int = 99999999,
        page: int = 1,
        offset: int = 100,
        sort: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """Get internal transactions for an address"""
        params = {
            'module': 'account',
            'action': 'txlistinternal',
            'address': address,
            'startblock': startblock,
            'endblock': endblock,
            'page': page,
            'offset': offset,
            'sort': sort
        }
        
        result = self._make_request(params)
        return result.get('result', [])
    
    def get_balance(self, address: str) -> str:
        """Get ETH balance for an address"""
        params = {
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest'
        }
        
        result = self._make_request(params)
        return result.get('result', '0')

