import json
import os
import requests
import time
from typing import List, Dict, Optional

# Configuration
API_KEY = "skS5fWcYWCjCNELhDJM6x6vsH0YGb3mB3jqHd32ASH32RvU119POX7XGz3eXnhGRXoO1jfYOc5LyuI1Yb01E3b"
ORDERS_FILE = "orders_data.json"
API_ENDPOINT = "https://api.ataix.kz/api/orders"
REQUEST_DELAY = 1  # Delay in seconds between API requests

def load_sell_orders() -> List[Dict]:
    """Load sell orders from the JSON file."""
    if not os.path.exists(ORDERS_FILE):
        print(f"⚠️ File {ORDERS_FILE} not found. Starting with an empty list.")
        return []
    with open(ORDERS_FILE, 'r') as file:
        return json.load(file)

def save_sell_orders(orders: List[Dict]) -> None:
    """Save updated sell orders back to the JSON file."""
    with open(ORDERS_FILE, 'w') as file:
        json.dump(orders, file, indent=4)

def check_order_status(order_id: str) -> Optional[Dict]:
    """Check the status and details of an order via API."""
    url = f"{API_ENDPOINT}/{order_id}"
    headers = {
        "accept": "application/json",
        "X-API-Key": API_KEY
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get('result', {})
    except requests.RequestException as e:
        print(f"⚠️ Error checking status for order {order_id}: {e}")
        return None

def calculate_profit(buy_order: Dict, sell_order: Dict) -> Dict:
    """Calculate net profit in USDT and percentage."""
    try:
        buy_cum_quote = float(buy_order.get('cumQuoteQuantity', 0))
        buy_commission = float(buy_order.get('cumCommission', 0))
        sell_cum_quote = float(sell_order.get('cumQuoteQuantity', 0))
        sell_commission = float(sell_order.get('cumCommission', 0))

        total_cost = buy_cum_quote + buy_commission
        total_revenue = sell_cum_quote - sell_commission
        profit_usdt = total_revenue - total_cost
        profit_percent = (profit_usdt / total_cost * 100) if total_cost != 0 else 0

        return {
            "usdt": round(profit_usdt, 4),
            "percent": round(profit_percent, 2)
        }
    except (ValueError, TypeError) as e:
        print(f"⚠️ Error calculating profit: {e}")
        return {"usdt": 0, "percent": 0}

def process_sell_orders():
    """Process all sell orders, update their status, and calculate profit if filled."""
    orders = load_sell_orders()
    updated_count = 0

    for order in orders:
        order_id = order.get('orderID')
        if not order_id:
            print("[❌] Missing orderID in order data.")
            continue

        print(f"[🔍] Checking sell order #{order_id}...")

        order_details = check_order_status(order_id)
        if not order_details:
            continue

        # Update order fields with API data
        order['status'] = order_details.get('status', order.get('status', 'unknown'))
        order['cumQuoteQuantity'] = order_details.get('cumQuoteQuantity', order.get('cumQuoteQuantity', '0'))
        order['cumCommission'] = order_details.get('cumCommission', order.get('cumCommission', '0'))

        if order['status'].lower() == 'filled':
            updated_count += 1
            print(f"[✅] Sell order #{order_id} is filled!")
            related_buy_order = order.get('related_buy_order', {})
            if related_buy_order and 'cumQuoteQuantity' in related_buy_order and 'cumCommission' in related_buy_order:
                profit = calculate_profit(related_buy_order, order_details)
                order['profit'] = profit
                print(f"[💰] Profit: {profit['usdt']} USDT ({profit['percent']}%)")
            else:
                print(f"[⚠️] No related buy order or missing data for profit calculation.")

        time.sleep(REQUEST_DELAY)

    save_sell_orders(orders)
    print(f"\n[📊] Processed {len(orders)} orders, updated {updated_count} filled orders.")
    print("[🗃] Updated order data saved to file.")

if __name__ == "__main__":
    process_sell_orders()
