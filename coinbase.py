import requests
import jwt
import time
import secrets
import json
import math
import logging
from config import load_settings, update_settings

class CoinbaseClient:
    def __init__(self):
        self.settings = load_settings()
        self.key_name = self.settings['key_name']
        self.key_secret = self.settings['key_secret'].replace("\\n", "\n")
        self.request_host = self.settings['request_host']
        self.base_url = f"https://{self.request_host}"

    def _generate_jwt(self, method, path):
        """Generate a JWT token for the given method and path"""
        uri = f"{method} {self.request_host}{path}"
        private_key_bytes = self.key_secret.encode('utf-8')
        private_key = jwt.algorithms.RSAAlgorithm.from_jwk(private_key_bytes)
        jwt_payload = {
            'sub': self.key_name,
            'iss': "cdp",
            'nbf': int(time.time()),
            'exp': int(time.time()) + 120,
            'uri': uri,
        }
        jwt_token = jwt.encode(
            jwt_payload,
            private_key,
            algorithm='RS256',
            headers={'kid': self.key_name, 'nonce': secrets.token_hex()},
        )
        return jwt_token

    def _make_request(self, method, path, payload=None):
        """Make a request to the Coinbase API"""
        url = f"{self.base_url}{path}"
        jwt_token = self._generate_jwt(method, path)
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request(method, url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', '10'))
                logging.info(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(method, path, payload)
            else:
                print(f"HTTP error for {url}: {e}")
                print(response.text)
                raise
        except Exception as e:
            print(f"Error making request to {url}: {e}")
            raise

    def get_current_price(self, product_id):
        path = self.settings['prices_path'].format(product_id=product_id)
        try:
            response = self._make_request('GET', path)
            return float(response.get('best_bid', response.get('trades', [{}])[0].get('price')))
        except Exception as e:
            logging.error(f"Error retrieving price for {product_id}: {e}")
            return None

    def place_market_order(self, product_id, side, usd_order_size=None, size=None):
        path = self.settings['orders_path']
        # Implement order placing logic
        pass

    def get_accounts(self):
        path = self.settings['accounts_path']
        try:
            response = self._make_request('GET', path)
            return response
        except Exception as e:
            logging.error(f"Error retrieving accounts: {e}")
            return []


    def get_price(self, product_id):
        path = self.settings['prices_path'].format(product_id=product_id)
        try:
            response = self._make_request('GET', path)
            return float(response.get('best_bid', response.get('trades', [{}])[0].get('price')))
        except Exception as e:
            logging.error(f"Error retrieving price for {product_id}: {e}")
            return None

    def refresh_balances_and_prices(self, settings):
        try:
            accounts = self.get_accounts()
            for account in accounts:
                network = account['currency']
                balance = float(account['balance'])
                if network not in settings:
                    settings[network] = {
                        'enabled': False,
                        'current_price': 1.0,
                        'current_cost_usd': -1,
                        'usd_value': 0.0,
                        'balance': balance,
                        'trend_status': None,
                        'previous_price': 0.0,
                        'enable_conversion': True
                    }

                if settings[network].get('enable_conversion', True):
                    current_price = self.get_price(f"{network}-USD")
                    if current_price is None:
                        settings[network]['enable_conversion'] = False
                        current_price = 1.0  # Set to 1.0 when no ticker is available
                else:
                    current_price = float(settings[network].get('current_price', 1.0))

                if network.upper() in ['USD', 'USDC']:
                    current_price = 1.0

                usd_value = balance * current_price

                self.update_coin_settings(settings, network, balance, current_price, usd_value)

        except Exception as e:
            logging.error(f"Error refreshing balances and prices: {e}")

    def update_coin_settings(self, settings, network, balance, current_price, usd_value):
        settings[network]['current_price'] = current_price
        settings[network]['usd_value'] = usd_value
        settings[network]['balance'] = balance
        if 'current_cost_usd' not in settings[network]:
            settings[network]['current_cost_usd'] = -1
        if 'enabled' not in settings[network]:
            settings[network]['enabled'] = False
        if 'trend_status' not in settings[network]:
            settings[network]['trend_status'] = None
        if 'previous_price' not in settings[network]:
            settings[network]['previous_price'] = current_price
        if 'enable_conversion' not in settings[network]:
            settings[network]['enable_conversion'] = True