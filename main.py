import os
from src.app import create_app

def main():
    api_key = os.getenv('ETHERSCAN_API_KEY')
    if not api_key:
        raise ValueError('ETHERSCAN_API_KEY environment variable is required')

    app = create_app(api_key=api_key)
    app.run(host='0.0.0.0', port=8888, debug=True)

if __name__ == '__main__':
    main()