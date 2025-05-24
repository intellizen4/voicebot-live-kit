import asyncio
import json
import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List, TypeVar, Callable, Awaitable
from functools import wraps

T = TypeVar('T')
DecoratedFunc = Callable[..., Awaitable[T]]

# Required fields to filter order information
required_fields = [
    "id", "order_number", "created_at", "updated_at", "processed_at", "financial_status",
    "fulfillment_status", "total_price", "subtotal_price", "total_tax", "currency",
    "email", "phone", "line_items", "shipping_address", "fulfillments",
    "payment_gateway_names", "total_discounts", "total_weight", "tags"
]


class ShopifyDataCollector:
    def __init__(self, shopify_access_token: str = None, shopify_base_url: str = None, 
                 temp_storage_path: str = 'temp_data'):
        self.temp_storage_path = temp_storage_path
        self.access_token = shopify_access_token
        self.BASE_URL = shopify_base_url
        self.shop_name = None
        
        # Extract shop name from base URL if provided
        if shopify_base_url:
            # Extract shop name from URL like https://shop-name.myshopify.com/admin/api/2025-01
            parts = shopify_base_url.split('//')
            if len(parts) > 1:
                domain = parts[1].split('/')[0]
                self.shop_name = domain.split('.')[0]
        
        # Set up headers if access token is provided
        if shopify_access_token:
            self.headers = {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": shopify_access_token
            }
        else:
            self.headers = None

        if not os.path.exists(temp_storage_path):
            os.makedirs(temp_storage_path)

    def _handle_auth_error(func: DecoratedFunc[T]) -> DecoratedFunc[T]:
        """Decorator to handle authentication errors"""
        @wraps(func)
        async def wrapper(self: 'ShopifyDataCollector', *args: Any, **kwargs: Any) -> Optional[T]:
            try:
                if not self.headers or not self.BASE_URL:
                    print("No credentials set. Please provide access token and base URL.")
                    return None
                    
                result = await func(self, *args, **kwargs)
                if isinstance(result, requests.Response) and result.status_code == 401:
                    print("Authentication failed. Please check your access token.")
                    return None
                return result
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print("Authentication failed. Please check your access token.")
                    return None
                raise
            except Exception as e:
                print(f"Error in {func.__name__}: {e}")
                return None
        return wrapper

    # Customer APIs
    @_handle_auth_error
    async def fetch_customer_id(self, phone: str) -> Optional[str]:
        """
        Fetches customer ID based on the phone number.

        Args:
            phone (str): Customer's phone number.

        Returns:
            Optional[str]: Customer ID if found, otherwise None.
        """
        # try:
        url = f"{self.BASE_URL}/customers.json?phone={phone}"
        if "https://" not in url:
            url = "https://" + url
        print("__________ HERE____________", url)
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        # response
        data_customers = response.json()
        
        print(data_customers)
        for customer in data_customers.get('customers', []):
            if phone == customer.get('phone'):
                print("customer",customer.get('id'))
                return customer.get('id')
        print("Customer ID not found.")
        return None
        # except Exception as e:
        #     print(f"Error in fetch_customer_id: {e}")
        #     return None

    @_handle_auth_error
    async def get_customer_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves details of a specific customer.
        """
        try:
            url = f"{self.BASE_URL}/customers/{customer_id}.json"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            return response.json().get('customer')
        except Exception as e:
            print(f"Error in get_customer_by_id: {e}")
            return None

    @_handle_auth_error
    async def get_all_customers(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves all customers from the store.
        """
        try:
            url = f"{self.BASE_URL}/customers.json"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            return response.json().get('customers', [])
        except Exception as e:
            print(f"Error in get_all_customers: {e}")
            return None

    # Order APIs
    @_handle_auth_error
    async def get_customer_orders(self, customer_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves orders for a customer and filters required fields.

        Args:
            customer_id (str): Customer ID.

        Returns:
            Optional[List[Dict[str, Any]]]: Filtered list of order details if successful, else None.
        """
        try:
            url = f"{self.BASE_URL}/orders.json?query=customer_id:{customer_id}&status=any"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            orders = response.json().get('orders', [])
            if orders:
                filtered_orders = [{'customer_id': customer_id, **
                                    {key: order.get(key) for key in required_fields}} for order in orders]
                return filtered_orders
            else:
                print(f"No orders found for customer ID: {customer_id}")
        except Exception as e:
            print(f"Error in get_customer_orders: {e}")
        return None

    @_handle_auth_error
    async def get_all_orders(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves all orders from the store.
        """
        try:
            url = f"{self.BASE_URL}/orders.json"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get('orders', [])
        except Exception as e:
            print(f"Error in get_all_orders: {e}")
            return None

    @_handle_auth_error
    async def cancel_order(self, order_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancels a specific order.
        """
        try:
            url = f"{self.BASE_URL}/orders/{order_id}/cancel.json"
            data = {"reason": reason} if reason else {}

            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()

            return True
        except Exception as e:
            print(f"Error in cancel_order: {e}")
            return False

    @_handle_auth_error
    async def update_order(self, order_id: str, email: Optional[str] = None, phone: Optional[str] = None,
                       address1: Optional[str] = None, address2: Optional[str] = None,
                       city: Optional[str] = None, last_name: Optional[str] = None,
                       province_code: Optional[str] = None,
                       country: Optional[str] = None, zip1: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Updates an order's email, phone, or shipping address if provided and stores response in a JSON file.

        Args:
            order_id (str): The ID of the order to update.
            email (Optional[str]): New email address.
            phone (Optional[str]): New phone number.
            address1 (Optional[str]): Street address.
            address2 (Optional[str]): Additional street address.
            city (Optional[str]): City name.
            last_name (Optional[str]): Last name for shipping address.
            province_code (Optional[str]): Province or state code.
            country (Optional[str]): Country.
            zip1 (Optional[str]): Zip or postal code.
        """
        try:
            # Step 1: Retrieve the current order details
            url = f"{self.BASE_URL}/orders/{order_id}.json"

            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            order_data = response.json().get("order")

            if not order_data:
                print(f"Order {order_id} not found.")
                return None

            # Step 2: Check fulfillment and cancellation status
            fulfillment_status = order_data.get("fulfillment_status")
            cancelled_at = order_data.get("cancelled_at")

            if fulfillment_status == "fulfilled":
                print(
                    f"Order {order_id} is already fulfilled. No updates will be made.")
                return None

            if cancelled_at is not None:
                print(
                    f"Order {order_id} is canceled. No updates will be made.")
                return None

            # Step 3: Prepare the update payload
            update_data = {"order": {"id": order_id}}

            if email:
                update_data["order"]["email"] = email
                update_data["order"]["contact_email"] = email
            if phone:
                update_data["order"]["phone"] = phone
            if address1 or address2 or city or last_name or country or province_code or zip1:
                update_data["order"]["shipping_address"] = {}
                if address1:
                    update_data["order"]["shipping_address"]["address1"] = address1
                if address2:
                    update_data["order"]["shipping_address"]["address2"] = address2
                if city:
                    update_data["order"]["shipping_address"]["city"] = city
                if last_name:
                    update_data["order"]["shipping_address"]["last_name"] = last_name
                if country:
                    update_data["order"]["shipping_address"]["country"] = country
                if province_code:
                    update_data["order"]["shipping_address"]["province_code"] = province_code
                if zip1:
                    update_data["order"]["shipping_address"]["province"] = zip1    

            # Step 4: Update the order
            response = requests.put(
                url, headers=self.headers, json=update_data)
            response.raise_for_status()

            print("Final Payload:", json.dumps(update_data, indent=4))

            order_data = response.json().get("order")
            if order_data:
                with open(f"order_{order_id}.json", "w") as json_file:
                    json.dump(order_data, json_file, indent=4)
                print(
                    f"Order {order_id} updated successfully. Data saved to order_{order_id}.json")

            return order_data
        except Exception as e:
            print(f"Error updating order {order_id}: {e}")
            return None

    # Product APIs
    @_handle_auth_error
    async def get_all_products(self) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieves all products from the store.
        """
        try:
            url = f"{self.BASE_URL}/products.json"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            products = response.json().get('products', [])
            return products
        except Exception as e:
            print(f"Error in get_all_products: {e}")
            return None

    @_handle_auth_error
    async def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves details of a specific product.
        """
        try:
            url = f"{self.BASE_URL}/products/{product_id}.json"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            return response.json().get('product')
        except Exception as e:
            print(f"Error in get_product_by_id: {e}")
            return None

    # Shop APIs
    @_handle_auth_error
    async def get_shop_details(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves shop information.
        """
        try:
            url = f"{self.BASE_URL}/shop.json"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            return response.json().get('shop')
        except Exception as e:
            print(f"Error in get_shop_details: {e}")
            return None



# Example usage
import asyncio

async def main():
    # Create an instance with your access token and store URL
    shopify_store_name = "softmaxai-parshva.myshopify.com"
    collector = ShopifyDataCollector(
        shopify_access_token="shpua_1645afdfc1efc8db22278c20a8b1787a",
        shopify_base_url=f"https://{shopify_store_name}/admin/api/2025-01"
    )
    
    # Fetch all customers
    customers = await collector.get_all_customers()
    print(f"Found {len(customers)} customers")
    
    # Fetch all orders
    orders = await collector.get_all_orders()
    print(f"Found {len(orders)} orders")

    customer_id = await collector.fetch_customer_id("+918200245825")
    order_id = await collector.get_customer_orders(customer_id)

    print(customer_id)
    for order in order_id:
        print(order['id'], order['order_number'])

    
    # Update an order
    updated_order = await collector.update_order(
        order_id="1234567890",
        email="customer@example.com",
        phone="+15551234567",
        address1="123 Main St"
    )
    
    # Collect and store all data
    # await collector.collect_and_store_data()

# if __name__ == "__main__":
#     asyncio.run(main())

    # Data Collection and Storage
    # async def collect_and_store_data(self) -> bool:
    #     """Collect and store all shop data"""
    #     if not self.headers or not self.BASE_URL:
    #         print("No credentials available. Please provide access token and base URL.")
    #         return False

    #     try:
    #         orders = await self.get_all_orders()
    #         shop_data = {
    #             'shop_details': await self.get_shop_details(),6587870413115 1010
# 6587869954363 1009
    #             'products': await self.get_all_products(),
    #             'customers': await self.get_all_customers(),
    #             'orders': orders,
    #             'metadata': {
    #                 'collected_at': datetime.now().isoformat(),
    #                 'shop_name': self.shop_name
    #             }
    #         }

    #         # Example of using the update_order method
    #         # Uncomment the following code if you want to update an order
    #         """
    #         updated_order = await self.update_order(
    #             order_id="YOUR_ORDER_ID",
    #             address1="123 Ship Street",
    #             address2="Apartment 5A",
    #             city="Ahmedabad",
    #             country="India",
    #             last_name="Jane4",
    #             phone="+911455566773",
    #             email="newemail@example.com",
    #             province_code="GJ",
    #             zip1="380001"
    #         )
    #         if updated_order:
    #             shop_data['update_orders'] = updated_order
    #         """

    #         if any(value for key, value in shop_data.items() if key != 'metadata'):
    #             self.save_temp_data(self.shop_name, shop_data)
    #             print(f"Data collected and stored for {self.shop_name}")
    #             return True
    #         else:
    #             print("No valid data collected.")
    #             return False

    #     except Exception as e:
    #         print(f"Error collecting data: {e}")
    #         return False

    # def save_temp_data(self, shop_name: str, data: Dict[str, Any]):
    #     """Save shop data to temporary storage."""
    #     try:
    #         if not shop_name:
    #             shop_name = "unknown_shop"
                
    #         # Create shop-specific directory
    #         shop_dir = os.path.join(
    #             self.temp_storage_path, shop_name.replace('.', '_'))
    #         if not os.path.exists(shop_dir):
    #             os.makedirs(shop_dir)

    #         # Save different data types to separate files
    #         for data_type, content in data.items():
    #             file_path = os.path.join(shop_dir, f"{data_type}.json")
    #             with open(file_path, 'w') as f:
    #                 json.dump(content, f, indent=2)

    #         print(f"Data saved for shop: {shop_name}")

    #     except Exception as e:
    #         print(f"Error saving data for shop {shop_name}: {e}")