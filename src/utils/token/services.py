import os
import requests


CMC_API_KEY = os.getenv("CMC_PRO_API_KEY")


def get_token_price(coin: str):
    """
    CoinMarketCap API를 사용하여 토큰 가격을 가져옵니다.
    
    Args:
        coin: 토큰 심볼 (예: "ETH", "BTC")
    
    Returns:
        dict: {"coin": "eth", "currency": "usd", "price": 2000.0}
        None: API 호출 실패 시
    """
    # API 키가 없으면 기본값 반환
    if not CMC_API_KEY:
        print(f"Warning: CMC_PRO_API_KEY not set. Using default price for {coin}")
        # ETH 기본값: $2000
        default_prices = {
            "ETH": 2000.0,
            "BTC": 40000.0,
            "USDT": 1.0,
            "USDC": 1.0,
        }
        return {
            "coin": coin.lower(),
            "currency": "usd",
            "price": default_prices.get(coin.upper(), 0.0)
        }
    
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": CMC_API_KEY
    }
    params = {
        "symbol": coin.upper(),
        "convert": "USD"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)

        if response.status_code != 200:
            print(f"Warning: CoinMarketCap API returned status {response.status_code}. Using default price for {coin}")
            # API 실패 시 기본값 사용
            default_prices = {
                "ETH": 2000.0,
                "BTC": 40000.0,
                "USDT": 1.0,
                "USDC": 1.0,
            }
            return {
                "coin": coin.lower(),
                "currency": "usd",
                "price": default_prices.get(coin.upper(), 0.0)
            }

        data = response.json()
        try:
            price = data["data"][coin.upper()]["quote"]["USD"]["price"]
        except (KeyError, TypeError):
            print(f"Warning: Failed to parse CoinMarketCap response for {coin}. Using default price.")
            default_prices = {
                "ETH": 2000.0,
                "BTC": 40000.0,
                "USDT": 1.0,
                "USDC": 1.0,
            }
            return {
                "coin": coin.lower(),
                "currency": "usd",
                "price": default_prices.get(coin.upper(), 0.0)
            }

        return {
            "coin": coin.lower(),
            "currency": "usd",
            "price": price
        }
    except requests.exceptions.RequestException as e:
        print(f"Warning: Network error calling CoinMarketCap API: {e}. Using default price for {coin}")
        default_prices = {
            "ETH": 2000.0,
            "BTC": 40000.0,
            "USDT": 1.0,
            "USDC": 1.0,
        }
        return {
            "coin": coin.lower(),
            "currency": "usd",
            "price": default_prices.get(coin.upper(), 0.0)
        }

