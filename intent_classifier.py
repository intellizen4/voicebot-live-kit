import openai
import re
import json
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field
import os

class OrderEntity(BaseModel):
    order_id: Optional[str] = Field(None, description="Order ID or number if mentioned")
    
class ContactEntity(BaseModel):
    email: Optional[str] = Field(None, description="Email address if present")
    phone: Optional[str] = Field(None, description="Phone number if present")
    
class AddressEntity(BaseModel):
    address1: Optional[str] = Field(None, description="First line of address")
    address2: Optional[str] = Field(None, description="Second line of address")
    city: Optional[str] = Field(None, description="City name")
    province_code: Optional[str] = Field(None, description="State or province")
    zip: Optional[str] = Field(None, description="ZIP or postal code")
    country: Optional[str] = Field(None, description="Country name")
    
class ProductEntity(BaseModel):
    product_type: Optional[str] = Field(None, description="Type of product mentioned")
    product_name: Optional[str] = Field(None, description="Specific product name if mentioned")
    attributes: Optional[Dict[str, str]] = Field(None, description="Product attributes like color, size, etc.")
    price_info: Optional[str] = Field(None, description="Any price-related information")
    
class StoreEntity(BaseModel):
    location: Optional[str] = Field(None, description="Store location if mentioned")
    hours: Optional[str] = Field(None, description="Store hours if mentioned")
    policy_type: Optional[str] = Field(None, description="Type of policy being asked about")

class EntityResponse(BaseModel):
    order: Optional[OrderEntity] = None
    contact: Optional[ContactEntity] = None
    address: Optional[AddressEntity] = None
    product: Optional[ProductEntity] = None
    store: Optional[StoreEntity] = None
    raw_text: str = Field(..., description="The original query text")

class IntentClassifier:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        openai.api_key = self.api_key

        self.llm = ChatOpenAI(temperature=0.2, model_name="gpt-4o", openai_api_key=os.getenv("OPENAI_API_KEY"))
        
        # Define the intents from the original code
        self.intents = [
            "product", 
            "order", 
            "update_order", 
            "cancel_order", 
            "store_info", 
            "general"
        ]
        
        # Create intent examples dictionary from the original code
        self.intent_examples = {
            "product": [
                "Do you have any blue t-shirts?",
                "What products do you sell?",
                "Tell me about your bestselling items",
                "How much does this product cost?",
                "Can you recommend something similar to this?",
                "Do you have this in other colors?",
                "What are the features of this product?",
                "Is this product in stock?",
                "When will this item be available?",
            ],
            "order": [
                "Where is my order?",
                "Can you check the status of my order?",
                "Has my order shipped yet?",
                "When will my order arrive?",
                "I want to track my order",
                "Can you tell me about my recent purchase?",
                "I haven't received my order yet",
                "Is my order being delivered today?",
                "What's the status of order #12345?",
            ],
            "update_order": [
                "I need to change my shipping address",
                "Can I update my email on my order?",
                "I entered the wrong phone number for my order",
                "I want to change the delivery option",
                "Need to modify my recent purchase",
                "Can you update my contact information?",
                "I put in the wrong address for my order",
                "Change my order details",
                "Update my order information",
            ],
            "cancel_order": [
                "I want to cancel my order",
                "How do I get a refund?",
                "I changed my mind about my purchase",
                "Please cancel order #12345",
                "I don't want this order anymore",
                "Can I return this item?",
                "I need to cancel my recent purchase",
                "Stop my order from being processed",
                "Cancel my entire order",
            ],
            "store_info": [
                "What are your store hours?",
                "Where is your store located?",
                "Tell me about your return policy",
                "How can I contact the store?",
                "What payment methods do you accept?",
                "Do you offer international shipping?",
                "What is your refund policy?",
                "How long does shipping take?",
                "Tell me about your company",
            ],
            "general": [
                "Hello there",
                "Thanks for your help",
                "Goodbye",
                "Who are you?",
                "What can you help me with?",
                "I need assistance",
                "Can you help me?",
                "I have a question",
                "Good morning",
            ],
        }

    def classify_intent(self, history, query: str) -> str:
        """
        Classify the intent of a user query using LLM.
        
        Args:
            query (str): The user's question or request
            
        Returns:
            str: The classified intent
        """
        # Format examples for the prompt
        examples_text = ""
        for intent, examples in self.intent_examples.items():
            # Add 3 examples for each intent to keep prompt size reasonable
            for i, example in enumerate(examples[:3]):
                examples_text += f"\nQuery: {example}\nIntent: {intent}\n"
        
        system_message = f"""You are an intent classification system for an e-commerce customer service platform.
        Classify the user's query into one of these intents:
        - product: Questions about products, items, prices, availability, recommendations, etc.
        - order: Questions about order status, tracking, delivery times, etc.
        - update_order: Requests to change order details like shipping address, email, phone, etc.
        - cancel_order: Requests to cancel orders or get refunds.
        - store_info: Questions about store hours, locations, policies, contact information, etc.
        
        Examples:
        {examples_text}

        
        Return only the intent name and nothing else. No explanations, no punctuation, just the single intent word.
        When the user enters their phone number, customer ID, or address details classify as 'update_order'.
        """
        
        prompt_template = PromptTemplate(
            input_variables=["history","query"],
            template=f"{system_message}\n\nHistory: {{history}}\n\nQuery: {{query}}\nIntent:"
        )
        
        chain = prompt_template | self.llm | StrOutputParser()
        response = chain.invoke({"history":history,"query": query})
        
        # Clean up response to get just the intent
        intent = response.strip().lower()
        
        # Ensure we return one of our valid intents
        if intent not in self.intents:
            # Default to general if we get an unexpected response
            return "store_info"
            
        return intent
    
    def extract_entities(self, query: str, intent: str) -> Dict[str, Any]:
        """
        Extract all relevant entities from the query using LLM.
        
        Args:
            query (str): The user's question or request
            intent (str): The classified intent
            
        Returns:
            Dict[str, Any]: Dictionary of extracted entities
        """
        # Create a tailored prompt based on the detected intent
        if intent == "order":
            return self.extract_order_entities(query)
        elif intent == "update_order":
            return self.extract_update_order_entities(query)
        elif intent == "cancel_order":
            return self.extract_cancel_order_entities(query)
        elif intent == "product":
            return self.extract_product_entities(query)
        elif intent == "store_info":
            return self.extract_store_info_entities(query)
        else:
            # For general intent, only extract basic entities
            return self.extract_basic_entities(query)
    
    def extract_order_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities related to order status queries"""
        system_prompt = """Extract all information related to an order status query.
        Focus on:
        1. Order IDs/numbers (look for patterns like #12345, order 12345, etc.)
        2. Timeframes mentioned (e.g., "ordered last week")
        3. Specific products mentioned in relation to the order
        4. Any customer identifiers (name, email, phone)
        
        Return a JSON object with all extracted information.
        If information is not present, set the value to null.
        If you're unsure about a value, use your best guess but mark it with "uncertain: true".
        """
        
        prompt = PromptTemplate(
            input_variables=["query"],
            template=f"{system_prompt}\n\nCustomer query: {{query}}\n\nJSON:"
        )
        
        try:
            result = prompt | self.llm | JsonOutputParser()
            entities = result.invoke({"query": query})
            return entities
        except Exception as e:
            # Fallback to regex extraction if LLM parsing fails
            return self.extract_order_entities_regex(query)
    
    def extract_update_order_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities related to order update requests"""
        system_prompt = """Extract all information related to an order update request.
        Focus on:
        1. Order ID/number if present
        2. Contact information (email, phone)
        3. Address details (complete address or parts like city, state, zip)
        4. What specifically needs to be updated (shipping address, email, phone, etc.)
        
        For addresses, extract as much detail as possible, including:
        - Street address (line 1, line 2)
        - City
        - State/Province
        - ZIP/Postal code
        - Country
        
        For phone numbers, standardize to E.164 format if possible.
        For emails, verify they contain @ and a domain.
        
        Return a JSON object with all extracted information.
        """
        
        prompt = PromptTemplate(
            input_variables=["query"],
            template=f"{system_prompt}\n\nCustomer query: {{query}}\n\nJSON:"
        )
        
        try:
            result = prompt | self.llm | JsonOutputParser()
            entities = result.invoke({"query": query})
            return entities
        except Exception as e:
            # Fallback to regex extraction if LLM parsing fails
            return self.extract_update_order_entities_regex(query)
    
    def extract_cancel_order_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities related to order cancellation requests"""
        system_prompt = """Extract all information related to an order cancellation request.
        Focus on:
        1. Order ID/number if present
        2. Reason for cancellation (if mentioned)
        3. Any timeframe mentioned (e.g., "ordered yesterday")
        4. Customer identifiers (name, email, phone)
        
        Return a JSON object with all extracted information.
        """
        
        prompt = PromptTemplate(
            input_variables=["query"],
            template=f"{system_prompt}\n\nCustomer query: {{query}}\n\nJSON:"
        )
        
        try:
            result = prompt | self.llm | JsonOutputParser()
            entities = result.invoke({"query": query})
            return entities
        except Exception as e:
            # Fallback to regex extraction if LLM parsing fails
            return self.extract_cancel_order_entities_regex(query)
    
    def extract_product_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities related to product queries"""
        system_prompt = """Extract all product-related information from this query.
        Focus on:
        1. Product type (e.g., shirt, shoes, electronics)
        2. Specific product name if mentioned
        3. Product attributes (color, size, material, etc.)
        4. Price information or budget constraints
        5. Preferences or requirements (e.g., "waterproof", "formal", "casual")
        
        Return a JSON object with all extracted information.
        """
        
        prompt = PromptTemplate(
            input_variables=["query"],
            template=f"{system_prompt}\n\nCustomer query: {{query}}\n\nJSON:"
        )
        
        try:
            result = prompt | self.llm | JsonOutputParser()
            entities = result.invoke({"query": query})
            return entities
        except Exception as e:
            # Simple fallback
            product_words = re.findall(r'\b(?:shirt|shoes|jacket|pants|dress|product|item)\b', query, re.IGNORECASE)
            return {"product_keywords": product_words if product_words else []}
    
    def extract_store_info_entities(self, query: str) -> Dict[str, Any]:
        """Extract entities related to store information queries"""
        system_prompt = """Extract all store-related information from this query.
        Focus on:
        1. What specific information is being requested (hours, location, policies)
        2. Any specific location mentioned
        3. Any specific policy type mentioned (returns, shipping, payment)
        
        Return a JSON object with all extracted information.
        """
        
        prompt = PromptTemplate(
            input_variables=["query"],
            template=f"{system_prompt}\n\nCustomer query: {{query}}\n\nJSON:"
        )
        
        try:
            result = prompt | self.llm | JsonOutputParser()
            entities = result.invoke({"query": query})
            return entities
        except Exception as e:
            # Simple fallback
            return {"query_type": "store_info"}
    
    def extract_basic_entities(self, query: str) -> Dict[str, Any]:
        """Extract basic entities for general queries"""
        return {"query": query}
    
    # Fallback regex-based extraction methods
    def extract_order_entities_regex(self, query: str) -> Dict[str, Any]:
        """Fallback to regex for extracting order entities"""
        entities = {}
        
        # Extract order ID
        order_id = self.extract_order_id_regex(query)
        if order_id:
            entities["order_id"] = order_id
            
        return entities
    
    def extract_update_order_entities_regex(self, query: str) -> Dict[str, Any]:
        """Fallback to regex for extracting update order entities"""
        entities = {}
        
        # Extract order ID
        order_id = self.extract_order_id_regex(query)
        if order_id:
            entities["order_id"] = order_id
            
        # Extract email
        email = self.extract_email_regex(query)
        if email:
            entities["email"] = email
            
        # Extract phone
        phone = self.extract_phone_regex(query)
        if phone:
            entities["phone"] = phone
            
        # Extract address
        address_info = self.extract_address_info_regex(query)
        if address_info:
            entities.update(address_info)
            
        return entities
    
    def extract_cancel_order_entities_regex(self, query: str) -> Dict[str, Any]:
        """Fallback to regex for extracting cancel order entities"""
        entities = {}
        
        # Extract order ID
        order_id = self.extract_order_id_regex(query)
        if order_id:
            entities["order_id"] = order_id
            
        return entities
    
    # Regex helper methods
    def extract_order_id_regex(self, query: str) -> Optional[str]:
        """Extract order ID from query using regex"""
        patterns = [
            r"order\s+(?:#|number|id|no\.?)\s*(\d+)",
            r"order\s+(\d+)",
            r"#(\d+)",
            r"(\d{6,})"  # Looks for 6+ digit numbers which might be order IDs
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, query, re.IGNORECASE)
            if matches:
                return matches.group(1)
        
        return None
    
    def extract_email_regex(self, query: str) -> Optional[str]:
        """Extract email address from query using regex"""
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        matches = re.search(pattern, query)
        if matches:
            return matches.group(0)
        return None
    
    def extract_phone_regex(self, query: str) -> Optional[str]:
        """Extract phone number from query using regex"""
        patterns = [
            r"\b(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?(?:\d{3}[-.\s]?\d{4})\b",
            r"\b\d{10}\b",
            r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, query)
            if matches:
                # Clean up the phone number
                phone = matches.group(0)
                phone = re.sub(r'[^\d+]', '', phone)  # Remove non-digit characters except +
                return phone
                
        return None
    
    def extract_address_info_regex(self, query: str) -> Dict[str, Any]:
        """Extract address information from query using regex"""
        address_info = {}
        
        # Extract address lines
        address_patterns = [
            (r"address(?:\s+\d+)?\s+(?:is|:)?\s+([^\.,]+)", "address1"),
            (r"address\s*line\s*1\s*(?:is|:)?\s+([^\.,]+)", "address1"),
            (r"address\s*line\s*2\s*(?:is|:)?\s+([^\.,]+)", "address2"),
        ]
        
        for pattern, key in address_patterns:
            matches = re.search(pattern, query, re.IGNORECASE)
            if matches:
                address_info[key] = matches.group(1).strip()
        
        # Extract city
        city_match = re.search(r"city\s+(?:is|:)?\s+([^\.,]+)", query, re.IGNORECASE)
        if city_match:
            address_info["city"] = city_match.group(1).strip()
        
        # Extract last name
        name_match = re.search(r"(?:last name|surname|family name)\s+(?:is|:)?\s+([^\.,]+)", query, re.IGNORECASE)
        if name_match:
            address_info["last_name"] = name_match.group(1).strip()
        
        # Extract country
        country_match = re.search(r"country\s+(?:is|:)?\s+([^\.,]+)", query, re.IGNORECASE)
        if country_match:
            address_info["country"] = country_match.group(1).strip()
        
        # Extract zip/postal code
        zip_match = re.search(r"(?:zip|postal|zip code|postal code)\s+(?:is|:)?\s+([^\.,\s]+)", query, re.IGNORECASE)
        if zip_match:
            address_info["zip"] = zip_match.group(1).strip()
        
        # Extract state/province
        state_match = re.search(r"(?:state|province)\s+(?:is|:)?\s+([^\.,]+)", query, re.IGNORECASE)
        if state_match:
            address_info["province_code"] = state_match.group(1).strip()
            
        return address_info

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Main method to process a query: classify intent and extract entities
        
        Args:
            query (str): The user's question or request
            
        Returns:
            Dict[str, Any]: Dictionary with intent and extracted entities
        """
        # Classify intent
        intent = self.classify_intent(query)
        
        # Extract entities based on intent
        entities = self.extract_entities(query, intent)
        
        # Return results
        return {
            "intent": intent,
            "entities": entities,
            "query": query
        }