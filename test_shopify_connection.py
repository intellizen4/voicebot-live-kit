#!/usr/bin/env python3
"""
Shopify Connection Test Script

This script tests your Shopify API connection and functionality.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from shopify_handler import ShopifyDataCollector

# Load environment variables
load_dotenv()

async def test_shopify_connection():
    """Test Shopify API connection and basic functionality."""
    print("🧪 Testing Shopify Connection")
    print("=" * 50)
    
    # Get credentials from environment or user input
    access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
    store_url = os.getenv('SHOPIFY_STORE_URL')
    
    if not access_token:
        access_token = input("Enter your Shopify access token: ").strip()
    
    if not store_url:
        store_url = input("Enter your Shopify store URL (e.g., your-store.myshopify.com): ").strip()
    
    if not access_token or not store_url:
        print("❌ Access token and store URL are required")
        return False
    
    # Construct the full API URL
    if not store_url.startswith('https://'):
        base_url = f"https://{store_url}/admin/api/2025-01"
    else:
        base_url = f"{store_url}/admin/api/2025-01"
    
    print(f"🔗 Testing connection to: {base_url}")
    print(f"🔑 Using access token: {access_token[:10]}...")
    
    try:
        # Initialize the Shopify collector
        shopify = ShopifyDataCollector(
            shopify_access_token=access_token,
            shopify_base_url=base_url
        )
        
        # Test 1: Get shop details
        print("\n📊 Test 1: Getting shop details...")
        shop_details = await shopify.get_shop_details()
        if shop_details:
            print(f"✅ Shop name: {shop_details.get('name', 'Unknown')}")
            print(f"✅ Shop domain: {shop_details.get('domain', 'Unknown')}")
            print(f"✅ Shop email: {shop_details.get('email', 'Unknown')}")
            print(f"✅ Currency: {shop_details.get('currency', 'Unknown')}")
        else:
            print("❌ Failed to get shop details")
            return False
        
        # Test 2: Get products count
        print("\n📦 Test 2: Getting products...")
        products = await shopify.get_all_products()
        if products is not None:
            print(f"✅ Found {len(products)} products")
            if products:
                first_product = products[0]
                print(f"✅ Sample product: {first_product.get('title', 'Unknown')}")
        else:
            print("❌ Failed to get products")
            return False
        
        # Test 3: Get customers count
        print("\n👥 Test 3: Getting customers...")
        customers = await shopify.get_all_customers()
        if customers is not None:
            print(f"✅ Found {len(customers)} customers")
        else:
            print("❌ Failed to get customers")
            return False
        
        # Test 4: Get orders count
        print("\n📋 Test 4: Getting orders...")
        orders = await shopify.get_all_orders()
        if orders is not None:
            print(f"✅ Found {len(orders)} orders")
        else:
            print("❌ Failed to get orders")
            return False
        
        # Test 5: Test customer lookup by phone (if you have a test phone number)
        test_phone = input("\n📞 Enter a phone number to test customer lookup (optional, press Enter to skip): ").strip()
        if test_phone:
            print(f"🔍 Looking up customer with phone: {test_phone}")
            customer_id = await shopify.fetch_customer_id(test_phone)
            if customer_id:
                print(f"✅ Found customer ID: {customer_id}")
                
                # Get customer orders
                customer_orders = await shopify.get_customer_orders(customer_id)
                if customer_orders:
                    print(f"✅ Customer has {len(customer_orders)} orders")
                else:
                    print("ℹ️  Customer has no orders")
            else:
                print("ℹ️  No customer found with that phone number")
        
        print("\n🎉 All tests passed! Your Shopify connection is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Shopify connection: {e}")
        return False

async def test_redis_connection():
    """Test Redis connection for store mappings."""
    print("\n🔴 Testing Redis Connection")
    print("=" * 30)
    
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        print("✅ Redis connection successful")
        
        # Check for existing store mappings
        pattern = "store:*"
        keys = redis_client.keys(pattern)
        print(f"📊 Found {len(keys)} store mappings in Redis")
        
        if keys:
            print("📋 Configured stores:")
            for key in keys:
                phone_number = key.replace("store:", "")
                store_data = redis_client.hgetall(key)
                store_name = store_data.get('store_name', 'Unknown')
                print(f"  📞 {phone_number} → {store_name}")
        else:
            print("ℹ️  No store mappings found. Run setup_shopify_stores.py to configure stores.")
        
        return True
        
    except redis.ConnectionError:
        print("❌ Cannot connect to Redis. Please make sure Redis is running.")
        return False
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False

async def main():
    """Main test function."""
    print("🚀 Shopify Integration Test Suite")
    print("=" * 60)
    
    # Test Redis first
    redis_ok = await test_redis_connection()
    
    # Test Shopify connection
    shopify_ok = await test_shopify_connection()
    
    print("\n📋 Test Summary")
    print("=" * 20)
    print(f"Redis Connection: {'✅ PASS' if redis_ok else '❌ FAIL'}")
    print(f"Shopify Connection: {'✅ PASS' if shopify_ok else '❌ FAIL'}")
    
    if redis_ok and shopify_ok:
        print("\n🎉 All systems are ready! Your Shopify integration is working.")
        print("\nNext steps:")
        print("1. Configure store mappings using setup_shopify_stores.py")
        print("2. Start your voicebot with: python intellizen_voicebot.py")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        
        if not redis_ok:
            print("   - Make sure Redis is running: redis-server")
        if not shopify_ok:
            print("   - Check your Shopify credentials and API permissions")

if __name__ == "__main__":
    asyncio.run(main())
