import os
import requests
import json
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv


load_dotenv()

# Required fields to filter order information
required_fields = [
    "id", "order_number", "created_at", "updated_at", "processed_at", "financial_status",
    "fulfillment_status", "total_price", "subtotal_price", "total_tax", "currency", 
    "email", "phone", "line_items", "shipping_address", "fulfillments", 
    "payment_gateway_names", "total_discounts", "total_weight", "tags"
]

# Shopify API headers (Make sure to set your own access token)
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": os.environ.get('X-Shopify-Access-Token', 'X-Shopify-Access-Token')
}

def fetch_customer_id(phone: str) -> Optional[str]:
    """
    Fetches customer ID based on the phone number.

    Args:
        phone (str): Customer's phone number.

    Returns:
        Optional[str]: Customer ID if found, otherwise None.
    """
    try:
        url = f"https://petroverusa.myshopify.com/admin/api/2024-04/customers.json?phone={phone}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data_customers = response.json()
        for customer in data_customers.get('customers', []):
            if phone == customer.get('phone'):
                return customer.get('id')
        print("Customer ID not found.")
    except Exception as e:
        print(f"Error in fetch_customer_id: {e}")
    return None

def get_customer_orders(customer_id: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieves orders for a customer and filters required fields.

    Args:
        customer_id (str): Customer ID.

    Returns:
        Optional[List[Dict[str, Any]]]: Filtered list of order details if successful, else None.
    """
    try:
        url = f"https://petroverusa.myshopify.com/admin/api/2024-04/orders.json?query=customer_id:{customer_id}&status=any"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        orders = response.json().get('orders', [])
        if orders:
            filtered_orders = [{'customer_id': customer_id, **{key: order.get(key) for key in required_fields}} for order in orders]
            return filtered_orders
        else:
            print(f"No orders found for customer ID: {customer_id}")
    except Exception as e:
        print(f"Error in get_customer_orders: {e}")
    return None

def fetch_order_details_by_phone(phone: str) -> str:
    """
    Fetches order details based on customer phone number.

    Args:
        phone (str): Customer's phone number.

    Returns:
        str: Order details or a message indicating the result.
    """
    customer_id = fetch_customer_id(phone)
    if customer_id:
        order_details = get_customer_orders(customer_id)
        if order_details:
            return str(json.dumps(order_details, indent=2))
        return f"No orders found for customer ID: {customer_id}"
    return f"Customer ID not found for phone number: {phone}"
