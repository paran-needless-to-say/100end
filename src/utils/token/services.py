import os
import requests

CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")

def get_token_price(coin: str):
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
