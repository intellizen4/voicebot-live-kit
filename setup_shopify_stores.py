#!/usr/bin/env python3
"""
Shopify Store Setup Script

This script helps you set up Redis mappings for your Shopify stores.
Each phone number can be mapped to a specific Shopify store.
"""

import redis
import os
from typing import Dict, Any

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def setup_store_mapping(phone_number: str, store_config: Dict[str, Any]):
    """
    Set up a store mapping in Redis for a specific phone number.
    
    Args:
        phone_number (str): The phone number that will be called
        store_config (Dict): Store configuration including:
            - store_name: Name of the store
            - store_details: Store description and policies
            - shopify_access_token: Shopify API access token
            - shopify_base_url: Shopify store URL (without https://)
            - transfer_number: Phone number for human transfer
    """
    redis_key = f"store:{phone_number}"
    
    # Set all store configuration in Redis
    for key, value in store_config.items():
        redis_client.hset(redis_key, key, value)
    
    print(f"✅ Store mapping created for phone number: {phone_number}")
    print(f"   Store: {store_config.get('store_name')}")
    print(f"   Shopify URL: {store_config.get('shopify_base_url')}")

def verify_store_mapping(phone_number: str):
    """Verify that a store mapping exists and is properly configured."""
    redis_key = f"store:{phone_number}"
    store_data = redis_client.hgetall(redis_key)
    
    if not store_data:
        print(f"❌ No store mapping found for phone number: {phone_number}")
        return False
    
    required_fields = ['store_name', 'shopify_access_token', 'shopify_base_url']
    missing_fields = [field for field in required_fields if not store_data.get(field)]
    
    if missing_fields:
        print(f"❌ Missing required fields for {phone_number}: {missing_fields}")
        return False
    
    print(f"✅ Store mapping verified for {phone_number}:")
    for key, value in store_data.items():
        # Mask sensitive information
        if 'token' in key.lower():
            display_value = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"   {key}: {display_value}")
    
    return True

def list_all_stores():
    """List all configured stores."""
    pattern = "store:*"
    keys = redis_client.keys(pattern)
    
    if not keys:
        print("No stores configured.")
        return
    
    print(f"Found {len(keys)} configured stores:")
    for key in keys:
        phone_number = key.replace("store:", "")
        store_data = redis_client.hgetall(key)
        store_name = store_data.get('store_name', 'Unknown')
        print(f"  📞 {phone_number} → {store_name}")

def delete_store_mapping(phone_number: str):
    """Delete a store mapping."""
    redis_key = f"store:{phone_number}"
    result = redis_client.delete(redis_key)
    
    if result:
        print(f"✅ Deleted store mapping for {phone_number}")
    else:
        print(f"❌ No store mapping found for {phone_number}")

def main():
    """Interactive setup for Shopify store mappings."""
    print("🏪 Shopify Store Setup")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Add new store mapping")
        print("2. Verify store mapping")
        print("3. List all stores")
        print("4. Delete store mapping")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            print("\n📝 Adding New Store Mapping")
            print("-" * 30)
            
            phone_number = input("Enter phone number (e.g., +1234567890): ").strip()
            if not phone_number:
                print("❌ Phone number is required")
                continue
            
            store_name = input("Enter store name: ").strip()
            store_details = input("Enter store details/policies: ").strip()
            shopify_access_token = input("Enter Shopify access token: ").strip()
            shopify_base_url = input("Enter Shopify store URL (e.g., your-store.myshopify.com): ").strip()
            transfer_number = input("Enter transfer phone number (optional): ").strip()
            
            if not all([store_name, shopify_access_token, shopify_base_url]):
                print("❌ Store name, access token, and base URL are required")
                continue
            
            store_config = {
                'store_name': store_name,
                'store_details': store_details,
                'shopify_access_token': shopify_access_token,
                'shopify_base_url': shopify_base_url,
                'transfer_number': transfer_number
            }
            
            setup_store_mapping(phone_number, store_config)
            
        elif choice == "2":
            phone_number = input("Enter phone number to verify: ").strip()
            if phone_number:
                verify_store_mapping(phone_number)
                
        elif choice == "3":
            list_all_stores()
            
        elif choice == "4":
            phone_number = input("Enter phone number to delete: ").strip()
            if phone_number:
                confirm = input(f"Are you sure you want to delete the mapping for {phone_number}? (y/N): ").strip().lower()
                if confirm == 'y':
                    delete_store_mapping(phone_number)
                    
        elif choice == "5":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    try:
        # Test Redis connection
        redis_client.ping()
        print("✅ Redis connection successful")
        main()
    except redis.ConnectionError:
        print("❌ Cannot connect to Redis. Please make sure Redis is running on localhost:6379")
    except Exception as e:
        print(f"❌ Error: {e}")
