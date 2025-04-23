import json
import requests
import time
from typing import Dict, List, Optional

# Configuration
API_CREDENTIALS = {
    "key": "skS5fWcYWCjCNELhDJM6x6vsH0YGb3mB3jqHd32ASH32RvU119POX7XGz3eXnhGRXoO1jfYOc5LyuI1Yb01E3b",  # Replace with your API key
    "endpoint": "https://api.ataix.kz/api/orders"
}
ORDERS_DATABASE = "orders_data.json"
REQUEST_DELAY = 1  # Delay between API requests in seconds


class OrderManager:
    def __init__(self):
        self.orders_data = self._read_data_file()

    @staticmethod
    def _read_data_file() -> List[Dict]:
        """Read the JSON file containing order data."""
        try:
            with open(ORDERS_DATABASE, 'r') as data_file:
                return json.load(data_file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _update_data_file(self) -> None:
        """Save updated order data back to the JSON file."""
        with open(ORDERS_DATABASE, 'w') as data_file:
            json.dump(self.orders_data, data_file, indent=4)

    def _api_request(self, method: str, path: str = "", data: Optional[Dict] = None) -> Optional[Dict]:
        """Make an API request to the exchange."""
        url = f"{API_CREDENTIALS['endpoint']}/{path}".rstrip('/')
        headers = {
            "accept": "application/json",
            "X-API-Key": API_CREDENTIALS['key']
        }
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=10
            )
            return response.json() if response.content else {}
        except requests.RequestException as e:
            print(f"⚠️ API request failed: {str(e)}")
            return None

    def check_order_status(self, order_id: str) -> Optional[str]:
        """Check the current status of an order."""
        result = self._api_request('GET', order_id)
        return result.get('result', {}).get('status') if result else None

    def create_sell_order(self, symbol: str, quantity: float, buy_price: float) -> Optional[Dict]:
        """Create a sell order at 2% above the buy price."""
        sell_price = round(buy_price * 1.02, 4)
        order_details = {
            "symbol": symbol,
            "side": "sell",
            "type": "limit",
            "quantity": quantity,
            "price": f"{sell_price:.4f}"
        }
        response = self._api_request('POST', data=order_details)
        return response.get('result') if response else None

    def process_orders(self) -> None:
        """Process all buy orders and create sell orders if filled."""
        new_sell_orders = []

        for order in self.orders_data:
            # Only process buy orders that haven't been handled yet
            if order.get('status', '').lower() != 'new' or order.get('side') != 'buy':
                continue

            order_id = order['orderID']
            print(f"[🔎] Checking order #{order_id}...")

            status = self.check_order_status(order_id)
            if not status:
                print(f"[❌] Failed to check status for order #{order_id}")
                continue

            if status.lower() == 'filled':
                print(f"[✅] Order #{order_id} is filled!")
                buy_price = float(order['price'])
                quantity = float(order['quantity'])
                sell_order = self.create_sell_order(order['symbol'], quantity, buy_price)

                if sell_order:
                    print(f"[🆕] Created sell order #{sell_order['orderID']}")
                    # Link the sell order to the original buy order
                    sell_order['related_buy_order'] = order_id
                    new_sell_orders.append(sell_order)
                    # Update the buy order status
                    order['status'] = 'filled'
                else:
                    print(f"[❌] Failed to create sell order for #{order_id}")

            time.sleep(REQUEST_DELAY)

        # Add new sell orders to the data and save
        self.orders_data.extend(new_sell_orders)
        self._update_data_file()
        print(f"\n[📊] Processed {len(self.orders_data)} orders, added {len(new_sell_orders)} sell orders.")
        print("[🗃] Updated order data saved to file.")


if __name__ == "__main__":
    manager = OrderManager()
    manager.process_orders()
