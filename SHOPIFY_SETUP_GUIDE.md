# Shopify Integration Setup Guide

## 🎯 Overview

Your voicebot already has a comprehensive Shopify integration! This guide will help you connect it to your Shopify store(s).

## 🚀 Quick Start

### 1. Set Up Environment Variables

Update your `env_export.sh` file with your Shopify credentials:

```bash
# Add these to your env_export.sh file
export SHOPIFY_ACCESS_TOKEN=your_shopify_access_token_here
export SHOPIFY_STORE_URL=your-store.myshopify.com
export TRANSFER_PHONE_NUMBER=your_transfer_phone_number
```

### 2. Test Your Connection

Run the connection test:

```bash
python test_shopify_connection.py
```

### 3. Set Up Store Mappings

Configure which phone numbers map to which Shopify stores:

```bash
python setup_shopify_stores.py
```

## 📋 Detailed Setup Steps

### Step 1: Get Shopify API Credentials

1. **Go to your Shopify Admin** → Apps → App and sales channel settings
2. **Create a Private App** or **Custom App**:
   - Go to "Develop apps" → "Create an app"
   - Configure API access scopes:
     - `read_orders` - Read order information
     - `write_orders` - Update orders
     - `read_customers` - Read customer information
     - `read_products` - Read product information
     - `read_shop` - Read shop information
3. **Install the app** and copy the **Admin API access token**

### Step 2: Configure Environment

Update your environment variables in `env_export.sh`:

```bash
# Load the environment
source env_export.sh
```

### Step 3: Set Up Redis Store Mappings

Your system supports multiple Shopify stores. Each phone number can be mapped to a different store:

```bash
# Run the interactive setup
python setup_shopify_stores.py
```

Or manually set up Redis mappings:

```bash
# Example: Map phone number +1234567890 to a Shopify store
redis-cli HSET "store:+1234567890" "store_name" "Your Store Name"
redis-cli HSET "store:+1234567890" "store_details" "Store description and policies"
redis-cli HSET "store:+1234567890" "shopify_access_token" "your_access_token"
redis-cli HSET "store:+1234567890" "shopify_base_url" "your-store.myshopify.com"
redis-cli HSET "store:+1234567890" "transfer_number" "+1234567891"
```

### Step 4: Test Everything

```bash
# Test Shopify connection
python test_shopify_connection.py

# Test Redis mappings
python setup_shopify_stores.py
# Choose option 3 to list all stores
```

## 🎤 Voice Features Available

Once connected, your voicebot can handle:

### 📦 **Product Information**
- "What products do you have?"
- "Tell me about [product name]"
- "Do you have [product type]?"

### 📋 **Order Management**
- "What's the status of my order?"
- "I need to update my shipping address"
- "I want to cancel my order"

### 🏪 **Store Information**
- "What are your business hours?"
- "What's your return policy?"
- "How can I contact you?"

### 👨‍💼 **Human Transfer**
- "I want to speak to a human"
- "Transfer me to customer service"

## 🔧 Troubleshooting

### Common Issues

1. **"No store data found for phone number"**
   - Run `python setup_shopify_stores.py` to configure store mappings
   - Make sure the phone number format matches (e.g., +1234567890)

2. **"Authentication failed"**
   - Check your Shopify access token
   - Verify API permissions in your Shopify app

3. **"Redis connection error"**
   - Make sure Redis is running: `redis-server`
   - Check Redis is accessible on localhost:6379

4. **"No orders found"**
   - Customer phone number might not match exactly
   - Check if customer exists in Shopify with that phone number

### Debug Commands

```bash
# Check Redis store mappings
redis-cli HGETALL "store:+1234567890"

# Test Shopify API directly
curl -H "X-Shopify-Access-Token: YOUR_TOKEN" \
     "https://your-store.myshopify.com/admin/api/2025-01/shop.json"

# Check Redis connection
redis-cli PING
```

## 📊 API Permissions Required

Your Shopify app needs these permissions:

- ✅ **read_orders** - Check order status
- ✅ **write_orders** - Update/cancel orders  
- ✅ **read_customers** - Find customers by phone
- ✅ **read_products** - Get product information
- ✅ **read_shop** - Get store details

## 🚀 Running the Voicebot

Once everything is configured:

```bash
# Start the voicebot
python intellizen_voicebot.py
```

The voicebot will:
1. Connect to LiveKit for voice processing
2. Look up store information from Redis based on the called phone number
3. Initialize Shopify connection with the store's credentials
4. Handle customer inquiries using AI-powered functions

## 📞 Multi-Store Support

You can support multiple Shopify stores by mapping different phone numbers to different stores:

```
+1234567890 → Store A (store-a.myshopify.com)
+1987654321 → Store B (store-b.myshopify.com)
+1555123456 → Store C (store-c.myshopify.com)
```

Each phone number will connect to its respective Shopify store automatically.

## 🎯 Next Steps

1. **Test the connection**: `python test_shopify_connection.py`
2. **Set up store mappings**: `python setup_shopify_stores.py`
3. **Start the voicebot**: `python intellizen_voicebot.py`
4. **Make a test call** to your configured phone number

Your Shopify integration is now ready! 🎉
