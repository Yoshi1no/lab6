import json
import requests
import time
from typing import Dict, List, Optional

# Конфигурация
API_CREDENTIALS = {
    "key": "skS5fWcYWCjCNELhDJM6x6vsH0YGb3mB3jqHd32ASH32RvU119POX7XGz3eXnhGRXoO1jfYOc5LyuI1Yb01E3b",
    "endpoint": "https://api.ataix.kz/api/orders"
}
ORDERS_DATABASE = "orders_data.json"
REQUEST_DELAY = 1  # Задержка между запросами в секундах


class OrderManager:
    def __init__(self):
        self.orders_data = self._read_data_file()

    @staticmethod
    def _read_data_file() -> List[Dict]:
        """Чтение данных из файла хранилища"""
        try:
            with open(ORDERS_DATABASE, 'r') as data_file:
                return json.load(data_file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _update_data_file(self) -> None:
        """Сохранение актуальных данных в файл"""
        with open(ORDERS_DATABASE, 'w') as data_file:
            json.dump(self.orders_data, data_file, indent=4)

    def _api_request(self, method: str, path: str = "", data: Optional[Dict] = None) -> Optional[Dict]:
        """Базовый метод для API-запросов"""
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
                timeout=20
            )
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Сетевая ошибка: {str(e)}")
            return None

    def check_order_state(self, order_id: str) -> Optional[str]:
        """Проверка текущего статуса ордера"""
        result = self._api_request('GET', str(order_id))
        return result.get('result', {}).get('status') if result else None

    def terminate_order(self, order_id: str) -> bool:
        """Отмена неисполненного ордера"""
        response = self._api_request('DELETE', str(order_id))
        return response.get('status') == 'success' if response else False

    def place_new_order(self, symbol: str, original_price: float) -> Optional[Dict]:
        """Размещение нового ордера с увеличенной ценой"""
        adjusted_price = round(original_price * 1.01, 4)
        order_details = {
            "symbol": symbol,
            "side": "buy",
            "type": "limit",
            "quantity": 1,
            "price": f"{adjusted_price:.4f}"
        }
        response = self._api_request('POST', data=order_details)
        return response.get('result') if response else None

    def _process_active_order(self, order: Dict) -> Optional[Dict]:
        """Обработка одного активного ордера"""
        order_id = order["orderID"]
        print(f"[🔎] Проверяем ордер #{order_id}...")

        current_status = self.check_order_state(order_id)
        if not current_status:
            return None

        if current_status.lower() == 'filled':
            print(f"[✅] Ордер #{order_id} успешно исполнен!")
            return {"action": "update", "status": "filled"}

        print(f"[🔄] Ордер #{order_id} требует обновления...")
        if self.terminate_order(order_id):
            new_order = self.place_new_order(
                order["symbol"],
                float(order["price"])
            )
            if new_order:
                print(f"[🆕] Создан новый ордер #{new_order['orderID']}")
                return {
                    "action": "replace",
                    "old_order": order_id,
                    "new_data": new_order
                }
        return None

    def execute_processing(self) -> None:
        """Основной цикл обработки ордеров"""
        updates = []
        replacements = []

        for order in self.orders_data:
            if order.get('status', '').lower() != 'new':
                continue

            result = self._process_active_order(order)
            time.sleep(REQUEST_DELAY)

            if result:
                if result["action"] == "update":
                    order["status"] = result["status"]
                    updates.append(order["orderID"])
                elif result["action"] == "replace":
                    order["status"] = "cancelled"
                    replacements.append(result["new_data"])

        self.orders_data.extend(replacements)
        self._update_data_file()

        print("\nРезультаты обработки:")
        print(f"Обновлено ордеров: {len(updates)}")
        print(f"Создано новых ордеров: {len(replacements)}")
        print("[🗃] Данные успешно сохранены!")


if __name__ == "__main__":
    processor = OrderManager()
    processor.execute_processing()