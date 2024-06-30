import os
import yaml
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_settings_file():
    try:
        settings_dir = Path("settings")
        settings_file = settings_dir / "settings.yaml"
        coins_settings_file = settings_dir / "coins_settings.yaml"
        trends_dir = Path("data/trends")

        settings_dir.mkdir(parents=True, exist_ok=True)
        trends_dir.mkdir(parents=True, exist_ok=True)

        if not settings_file.exists():
            create_default_settings_file(settings_file)
            logging.info(f"Created default settings file at {settings_file}")

        if not coins_settings_file.exists():
            create_default_coins_settings_file(coins_settings_file)
            logging.info(f"Created default coins settings file at {coins_settings_file}")
    except Exception as e:
        logging.error(f"Error ensuring settings file: {e}")

def create_default_settings_file(settings_file):
    default_settings = {
        "key_name": os.getenv("COINBASE_KEY_NAME", "organizations/{org_id}/apiKeys/{key_id}"),
        "key_secret": os.getenv("COINBASE_KEY_SECRET", ""),
        "request_host": "api.coinbase.com",
        "accounts_path": "/api/v3/brokerage/accounts",
        "prices_path": "/api/v3/brokerage/products/{product_id}/ticker",
        "orders_path": "/api/v3/brokerage/orders",
        "spend_account": "USD",
        "refresh_interval": 60,
        "transaction_fee": 0.5,
        "sale_threshold": 10,
        "loss_limit": 5
    }

    comments = {
        "key_name": "Coinbase Developer Platform API key name",
        "key_secret": "The private key for the API, ensure newlines are escaped with \\n",
        "request_host": "The host for the Coinbase API",
        "accounts_path": "The endpoint path for fetching account information",
        "prices_path": "The endpoint path for fetching current prices. {product_id} will be replaced with the actual product ID",
        "orders_path": "The endpoint path for creating orders",
        "spend_account": "The account used for spending, default is USD",
        "refresh_interval": "Interval in seconds to refresh prices",
        "transaction_fee": "Transaction fee percentage",
        "sale_threshold": "Sale threshold percentage",
        "loss_limit": "Loss limit percentage to trigger a sell"
    }

    with open(settings_file, "w") as f:
        yaml.dump(default_settings, f, default_flow_style=False, sort_keys=False)

    with open(settings_file, "r") as f:
        lines = f.readlines()

    with open(settings_file, "w") as f:
        for line in lines:
            key = line.split(":")[0].strip()
            if key in comments:
                f.write(f"# {comments[key]}\n")
            f.write(line)

def create_default_coins_settings_file(coins_settings_file):
    default_coins_settings = {}
    with open(coins_settings_file, "w") as f:
        yaml.dump(default_coins_settings, f)

def load_settings():
    ensure_settings_file()
    settings_file = Path("settings/settings.yaml")
    try:
        with open(settings_file, "r") as f:
            settings = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        return {}

    if not settings['key_name'] or not settings['key_secret']:
        settings['key_name'] = input("Enter your Coinbase API key name: ")
        settings['key_secret'] = input("Enter your Coinbase API key secret: ").replace("\\n", "\n")
        update_settings(settings)

    return settings

def load_coins_settings():
    ensure_settings_file()
    coins_settings_file = Path("settings/coins_settings.yaml")
    try:
        with open(coins_settings_file, "r") as f:
            coins_settings = yaml.safe_load(f) or {}
        return coins_settings
    except Exception as e:
        logging.error(f"Error loading coins settings: {e}")
        return {}

def save_trends(network, trends):
    trends_file = Path(f"data/trends/{network}.yaml")
    try:
        with open(trends_file, "w") as f:
            yaml.dump(trends, f)
    except Exception as e:
        logging.error(f"Error saving trends for {network}: {e}")

def load_trends(network):
    trends_file = Path(f"data/trends/{network}.yaml")
    try:
        if trends_file.exists():
            with open(trends_file, "r") as f:
                return yaml.safe_load(f)
        return []
    except Exception as e:
        logging.error(f"Error loading trends for {network}: {e}")
        return []

def update_settings(settings):
    try:
        with open("settings/settings.yaml", "w") as f:
            yaml.dump(settings, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logging.error(f"Error updating settings: {e}")

def update_coins_settings(settings):
    try:
        with open("settings/coins_settings.yaml", "w") as f:
            yaml.dump(settings, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logging.error(f"Error updating coins settings: {e}")
