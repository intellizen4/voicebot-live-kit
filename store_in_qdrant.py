import asyncio
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from shopify_handler import ShopifyDataCollector  # Import your original class

# Qdrant and OpenAI API keys (replace with actual values)
QDRANT_URL = 'YOUR_QDRANT_URL'
QDRANT_API_KEY = 'YOUR_QDRANT_API_KEY'
OPENAI_API_KEY = 'YOUR_OPENAI_API_KEY'

class QdrantStore:
    def __init__(self, collection_name="shopify_products"):
        """Initialize Qdrant client."""
        self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self.collection_name = collection_name
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

        # Check if collection exists, create if not
        if not self.client.collection_exists(collection_name=self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)  # 1536 is for OpenAI embeddings
            )

    def store_products(self, products, shop_name):
        """Store product details into Qdrant VDB."""
        if not products:
            print(f"No products to store for {shop_name}.")
            return

        documents = [
            Document(
                page_content=f"Product: {p['title']}\nDescription: {p.get('body_html', '')}\nPrice: {p.get('variants', [{}])[0].get('price', 'N/A')}",
                metadata={
                    "type": "shopify_product",
                    "store": shop_name,
                    "product_id": p["id"],
                    "title": p["title"],
                    "vendor": p.get("vendor", "N/A"),
                    "product_type": p.get("product_type", "N/A"),
                    "tags": p.get("tags", "").split(","),
                }
            )
            for p in products
        ]

        # Store in Qdrant
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                {
                    "id": doc.metadata["product_id"], 
                    "vector": list(self.embeddings.embed_query(doc.page_content)), 
                    "payload": doc.metadata
                }
                for doc in documents
            ]
        )
        print(f"Stored {len(products)} products for {shop_name} in Qdrant.")

async def main():
    shopify = ShopifyDataCollector()
    if not shopify.setup_credentials():
        print("No valid credentials found.")
        return

    products = await shopify.get_all_products()
    if products:
        qdrant = QdrantStore(str(shopify.get_shop_name()))
        qdrant.store_products(products, shopify.shop_name)
    else:
        print("No products fetched.")

if __name__ == "__main__":
    asyncio.run(main())
