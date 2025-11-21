import os
import requests


CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")


def get_token_price(coin: str):
    """
    토큰 가격을 가져옵니다 (기본값 사용)
    CoinMarketCap API Rate Limit 회피를 위해 API 호출 비활성화
    
    Args:
        coin: 토큰 심볼 (예: "ETH", "BTC")
    
    Returns:
        dict: {"coin": "eth", "currency": "usd", "price": 2000.0}
    """
    # 기본 가격 정의
    default_prices = {
        "ETH": 2000.0,
        "BTC": 40000.0,
        "USDT": 1.0,
        "USDC": 1.0,
        "DAI": 1.0,
        "WETH": 2000.0,
        "WBTC": 40000.0,
        "MATIC": 0.8,
        "BNB": 300.0,
    }
    
    return {
        "coin": coin.lower(),
        "currency": "usd",
        "price": default_prices.get(coin.upper(), 0.0)
    }
