import asyncio
import os
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

class QdrantSearcher:
    """A class to search for relevant documents and products in Qdrant."""
    
    def __init__(
            self,
            qdrant_url: str = os.getenv('QDRANT_URL', 'YOUR_QDRANT_URL'),
            qdrant_api_key: str = os.getenv('QDRANT_API_KEY', 'YOUR_QDRANT_API_KEY'),
            openai_api_key: str = os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_API_KEY'),
            document_collection: str = "document_store",
            product_collection: str = "softmaxai-parshva.myshopify.com"
        ):
        """Initialize the Qdrant searcher with necessary configurations."""
        self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
        self.document_collection = document_collection
        self.product_collection = product_collection
        self.embeddings_model = OpenAIEmbeddings(openai_api_key=openai_api_key)
    
    async def _get_embedding(self, text: str) -> List[float]:
        """Generate an embedding for the query text."""
        return await asyncio.to_thread(self.embeddings_model.embed_query, text)
    
    async def get_store_details(self, store_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve store details from Qdrant based on store name.
        
        Args:
            store_name (str): The name of the store to retrieve details for.
            
        Returns:
            Optional[Dict[str, Any]]: Store details if found, None otherwise.
        """
        try:
            # Create filter to find documents with store_details for this store
            search_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="store",
                        match=qdrant_models.MatchValue(value=store_name)
                    )
                ]
            )
            
            # First try to find documents that have store_details in metadata
            points = self.qdrant_client.scroll(
                collection_name=self.document_collection,
                scroll_filter=search_filter,
                limit=100  # We'll check through several documents
            )[0]  # Get the first page of results
            
            # Look for any points with store_details in metadata
            for point in points:
                if "store_details" in point.payload:
                    return {
                        "store_name": store_name,
                        "store_details": point.payload["store_details"],
                        "source": point.payload.get("source", "Unknown"),
                    }
            
            # If no direct store_details found, try to generate a summary from documents
            if points:
                # Create a query embedding for "store information" to find relevant documents
                query_embedding = await self._get_embedding("store information description about")
                
                # Search for documents that might contain store information
                search_results = self.qdrant_client.search(
                    collection_name=self.document_collection,
                    query_vector=query_embedding,
                    query_filter=search_filter,
                    limit=5  # Get a few most relevant documents
                )
                
                # Combine text from these documents (if any found)
                if search_results:
                    combined_text = "\n\n".join([
                        result.payload.get("text", "")[:1000]  # Take first 1000 chars from each
                        for result in search_results
                    ])
                    
                    # Return the best-effort store details
                    return {
                        "store_name": store_name,
                        "store_details": f"Store information compiled from {len(search_results)} documents",
                        "text_sample": combined_text[:500] + "...",
                        "note": "No explicit store_details found; this is compiled from relevant documents"
                    }
            
            # No store details found
            return None
            
        except Exception as e:
            print(f"Error retrieving store details for {store_name}: {str(e)}")
            return None
    
    async def search_documents(self, 
                              query: str, 
                              store_name: Optional[str] = None,
                              doc_type: Optional[str] = None,
                              source: Optional[str] = None,
                              limit: int = 5,
                              score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Search for relevant documents in Qdrant.
        
        Args:
            query (str): The search query.
            store_name (Optional[str]): Filter by store name.
            doc_type (Optional[str]): Filter by document type (e.g., "pdf_document", "web_scrape").
            source (Optional[str]): Filter by source (e.g., specific URL or filename).
            limit (int): Maximum number of results to return.
            score_threshold (float): Minimum relevance score (0-1).
            
        Returns:
            List[Dict[str, Any]]: List of matching documents with their metadata.
        """
        try:
            # Generate embedding for the query
            query_embedding = await self._get_embedding(query)
            
            # Build filter conditions
            filter_conditions = []
            
            if store_name:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="store",
                        match=qdrant_models.MatchValue(value=store_name)
                    )
                )
            
            if doc_type:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="type",
                        match=qdrant_models.MatchValue(value=doc_type)
                    )
                )
            
            if source:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="source",
                        match=qdrant_models.MatchValue(value=source)
                    )
                )
            
            # Combine filter conditions if any
            search_filter = None
            if filter_conditions:
                search_filter = qdrant_models.Filter(
                    must=filter_conditions
                )
            
            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.document_collection,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )
            
            # Format results
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "metadata": {
                        k: v for k, v in result.payload.items() if k != "text"
                    }
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching documents: {str(e)}")
            return []
    
    async def search_products(self, 
                             query: str, 
                             store_name: Optional[str] = None,
                             product_type: Optional[str] = None,
                             vendor: Optional[str] = None,
                             tags: Optional[List[str]] = None,
                             limit: int = 5,
                             score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Search for relevant products in Qdrant.
        
        Args:
            query (str): The search query.
            store_name (Optional[str]): Filter by store name.
            product_type (Optional[str]): Filter by product type.
            vendor (Optional[str]): Filter by vendor.
            tags (Optional[List[str]]): Filter by one or more tags.
            limit (int): Maximum number of results to return.
            score_threshold (float): Minimum relevance score (0-1).
            
        Returns:
            List[Dict[str, Any]]: List of matching products with their metadata.
        """
        try:
            # Generate embedding for the query
            query_embedding = await self._get_embedding(query)
            
            # Build filter conditions
            filter_conditions = []
            
            # Always add a condition to filter for shopify_product type
            filter_conditions.append(
                qdrant_models.FieldCondition(
                    key="type",
                    match=qdrant_models.MatchValue(value="shopify_product")
                )
            )
            
            if store_name:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="store",
                        match=qdrant_models.MatchValue(value=store_name)
                    )
                )
            
            if product_type:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="product_type",
                        match=qdrant_models.MatchValue(value=product_type)
                    )
                )
            
            if vendor:
                filter_conditions.append(
                    qdrant_models.FieldCondition(
                        key="vendor",
                        match=qdrant_models.MatchValue(value=vendor)
                    )
                )
            
            if tags and len(tags) > 0:
                tag_conditions = [
                    qdrant_models.FieldCondition(
                        key="tags",
                        match=qdrant_models.MatchValue(value=tag)
                    )
                    for tag in tags
                ]
                
                # Any of the tags should match (OR condition)
                filter_conditions.append(
                    qdrant_models.Filter(
                        should=tag_conditions,
                        should_score=1  # At least one must match
                    )
                )
            
            # Combine filter conditions
            search_filter = qdrant_models.Filter(
                must=filter_conditions
            )
            
            # Search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.product_collection,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )
            
            # Format results
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "title": result.payload.get("title", ""),
                    "product_id": result.payload.get("product_id", ""),
                    "vendor": result.payload.get("vendor", ""),
                    "product_type": result.payload.get("product_type", ""),
                    "tags": result.payload.get("tags", []),
                    "store": result.payload.get("store", "")
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching products: {str(e)}")
            return []
    
    async def search_all(self,
                        query: str,
                        store_name: Optional[str] = None,
                        limit: int = 10,
                        score_threshold: float = 0.7) -> Dict[str, List]:
        """
        Search for both documents and products in one call.
        
        Args:
            query (str): The search query.
            store_name (Optional[str]): Filter by store name.
            limit (int): Maximum number of results per category.
            score_threshold (float): Minimum relevance score (0-1).
            
        Returns:
            Dict[str, List]: Dictionary with "documents" and "products" keys.
        """
        # Run both searches concurrently
        document_results, product_results = await asyncio.gather(
            self.search_documents(query, store_name=store_name, limit=limit, score_threshold=score_threshold),
            self.search_products(query, store_name=store_name, limit=limit, score_threshold=score_threshold)
        )
        
        return {
            "documents": document_results,
            "products": product_results
        }
    
    async def search_by_metadata(self,
                                field: str,
                                value: Any,
                                collection_name: Optional[str] = None,
                                limit: int = 100) -> List[Dict]:
        """
        Search for documents or products by exact metadata field matching.
        
        Args:
            field (str): The metadata field to match against.
            value (Any): The value to match.
            collection_name (Optional[str]): Which collection to search (defaults to document_store).
            limit (int): Maximum number of results to return.
            
        Returns:
            List[Dict]: List of matching items.
        """
        try:
            # Default to document collection if not specified
            collection = collection_name or self.document_collection
            
            # Create filter
            search_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key=field,
                        match=qdrant_models.MatchValue(value=value)
                    )
                ]
            )
            
            # Search in Qdrant without using vector similarity
            search_results = self.qdrant_client.scroll(
                collection_name=collection,
                scroll_filter=search_filter,
                limit=limit
            )
            
            # Format results from the first page (scroll returns tuple with (points, next_page_offset))
            formatted_results = []
            for point in search_results[0]:
                formatted_results.append({
                    "id": point.id,
                    **point.payload
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching by metadata: {str(e)}")
            return []

    async def get_all_store_names(self) -> List[str]:
        """
        Get a list of all unique store names in the document collection.
        
        Returns:
            List[str]: List of unique store names.
        """
        try:
            # We'll use the scroll API to get all points and extract unique store names
            store_names = set()
            offset = None
            limit = 1000  # Batch size for retrieval
            
            while True:
                # Get a batch of points
                points, offset = self.qdrant_client.scroll(
                    collection_name=self.document_collection,
                    limit=limit,
                    offset=offset
                )
                
                # Extract store names from this batch
                for point in points:
                    if "store" in point.payload:
                        store_names.add(point.payload["store"])
                
                # If no more points (offset is None), break the loop
                if offset is None:
                    break
            
            return sorted(list(store_names))
            
        except Exception as e:
            print(f"Error getting store names: {str(e)}")
            return []

# Example usage
async def example_usage():
    # Create the searcher
    searcher = QdrantSearcher(
        qdrant_url=os.getenv('QDRANT_URL', 'YOUR_QDRANT_URL'),
        qdrant_api_key=os.getenv('QDRANT_API_KEY', 'YOUR_QDRANT_API_KEY'),
        openai_api_key=os.getenv('OPENAI_API_KEY', 'YOUR_OPENAI_API_KEY')
    )
    
    # Example 1: Get store details
    store_details = await searcher.get_store_details("example_store")
    if store_details:
        print(f"Store details for example_store: {store_details['store_details']}")
    else:
        print("No store details found.")
    
    # Example 2: Get all store names
    all_stores = await searcher.get_all_store_names()
    print(f"Found {len(all_stores)} stores: {', '.join(all_stores[:5])}...")
    
    # Example 3: Search for documents about "return policy" for a specific store
    documents = await searcher.search_documents(
        query="return policy",
        store_name="example_store",
        doc_type="pdf_document"
    )
    print(f"Found {len(documents)} documents about return policies.")
    
    # Example 4: Search for products related to "wooden furniture"
    products = await searcher.search_products(
        query="wooden furniture",
        store_name="example_store",
        product_type="furniture"
    )
    print(f"Found {len(products)} furniture products.")
    
    # Example 5: Search for both documents and products in one call
    results = await searcher.search_all(
        query="organic cotton",
        store_name="example_store"
    )
    print(f"Found {len(results['documents'])} documents and {len(results['products'])} products.")

if __name__ == "__main__":
    asyncio.run(example_usage())