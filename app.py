import os
from dotenv import load_dotenv
from src.create_app import create_app

load_dotenv()

api_key = os.getenv('ETHERSCAN_API_KEY')
if not api_key:
    raise ValueError('ETHERSCAN_API_KEY environment variable is required')

app = create_app(api_key=api_key)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
