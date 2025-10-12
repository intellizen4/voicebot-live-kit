import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Annotated
from datetime import datetime
from redis import Redis
import aiohttp

from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import AutoSubscribe, JobContext, JobProcess, WorkerOptions, cli, llm, metrics
from livekit.agents.pipeline import VoicePipelineAgent, AgentCallContext, AgentTranscriptionOptions
from livekit.plugins import deepgram, openai, silero
from livekit.protocol.sip import TransferSIPParticipantRequest

import sqlalchemy
import pymysql
import os
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy import text

from intent_classifier import IntentClassifier
from shopify_handler import ShopifyDataCollector
from retrieved_documents import QdrantSearcher

# Setup logging
logger = logging.getLogger("shopify-assistant")
logger.setLevel(logging.INFO)

# Initialize Redis client
redis_client = Redis(host='10.207.166.35', port=6379, db=0, decode_responses=True)
load_dotenv()
try:
    redis_client.ping()
    logger.info("Redis connection successful")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")

# Global variables to be set during participant connection
store_name = None
store_details = None
shopify_access_token = None
shopify_base_url = None
called_number = None
caller_number = None
customer_id = None

# Initialize core components
intent_classifier = IntentClassifier()
qdrant_searcher = QdrantSearcher()

def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """Create a connection pool to a Cloud SQL instance."""
    instance_connection_name = os.environ.get('SQL_INSTANCE', 'YOUR_SQL_INSTANCE')
    db_user = os.environ.get('DB_USER', 'USER_NAME')
    db_pass = os.environ.get('DB_PASS', 'PASSWORD')
    db_name = os.environ.get('DB_NAME', 'DB_NAME')
    ip_type = IPTypes.PRIVATE if os.environ.get("PRIVATE_IP") else IPTypes.PUBLIC
    
    connector = Connector(ip_type)
    
    def getconn() -> pymysql.connections.Connection:
        conn: pymysql.connections.Connection = connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn
    
    pool = sqlalchemy.create_engine("mysql+pymysql://", creator=getconn)
    return pool

# Initialize database connection
try:
    engine = connect_with_connector()
    logger.info("Database connection established")
except Exception as e:
    logger.error(f"Failed to connect to database: {e}")
    engine = None

def insert_conversation_to_db(conversation_data):
    """Insert a conversation record into the database."""
    if not engine:
        logger.error("Database connection not available")
        return False
    
    connection = engine.connect()
    insert_query = """
    INSERT INTO Conversations
        (Conversation, User_ID, Store_ID, Session_ID, Session_Time,
         Duration_of_Call, Call_Reason, Escalation, Query_Type)
    VALUES
        (:Conversation, :User_ID, :Store_ID, :Session_ID, :Session_Time,
         :Duration_of_Call, :Call_Reason, :Escalation, :Query_Type)
    """
    try:
        connection.execute(
            sqlalchemy.text(insert_query),
            parameters={
                'Conversation': conversation_data['Conversation'],
                'User_ID': conversation_data['User_ID'],
                'Store_ID': conversation_data['Store_ID'],
                'Session_ID': conversation_data['Session_ID'],
                'Session_Time': conversation_data['Session_Time'],
                'Duration_of_Call': conversation_data['Duration_of_Call'],
                'Call_Reason': conversation_data['Call_Reason'],
                'Escalation': conversation_data['Escalation'],
                'Query_Type': conversation_data['Query_Type']
            }
        )
        connection.commit()
        logger.info(f"Conversation saved to database. Session ID: {conversation_data['Session_ID']}")
        return True
    except Exception as e:
        logger.error(f"Database error: {e}")
        return False
    finally:
        connection.close()

def get_store_from_redis(phone_number: str):
    """Retrieve store details from Redis based on phone number."""
    if not phone_number:
        logger.error("No phone number provided for Redis lookup")
        return None, None, None, None
    
    redis_key = f"store:{phone_number}"
    try:
        store_data = redis_client.hgetall(redis_key)
        if not store_data:
            logger.warning(f"No store data found for phone number: {phone_number}")
            return None, None, None, None
        
        logger.info(f"Found store data for {phone_number}: {store_data.get('store_name')}")
        return (
            store_data.get("store_name"), 
            store_data.get("store_details"), 
            store_data.get("shopify_access_token"),
            store_data.get("shopify_base_url")
        )
    except Exception as e:
        logger.error(f"Redis error: {e}")
        return None, None, None, None


class ShopifyFunctions(llm.FunctionContext):
    """Function context for Shopify operations that can be called by the LLM."""
    
    def __init__(self, shopify: ShopifyDataCollector = None, qdrant_searcher: QdrantSearcher = None, room_ctx = None, room_name: str = None):
        super().__init__()
        self.room_name = room_name
        self.shopify = shopify
        self.qdrant_searcher = qdrant_searcher
        self.intent_classifier = IntentClassifier()
        self.room_ctx = room_ctx
    
    @llm.ai_callable()
    async def get_product_information(
        self,
        product_query: Annotated[
            str, llm.TypeInfo(description="The product search query or product name")
        ],
    ):
        """
        Search for product information based on the customer's product query.
        This function returns product details like name, price, availability, and descriptions.
        """
        agent = AgentCallContext.get_current().agent
        await agent.say("Let me look up that product information for you.", add_to_chat_ctx=True)
        
        try:
            if not self.shopify or not self.qdrant_searcher:
                self.shopify = ShopifyDataCollector(
                    shopify_access_token=shopify_access_token,
                    shopify_base_url=shopify_base_url
                )
                self.qdrant_searcher = QdrantSearcher()
            
            # Search for products
            product_results = await self.qdrant_searcher.search_products(
                query=product_query,
                store_name=store_name,
                limit=3,
                score_threshold=0.6
            )
            
            # Search for product documentation
            doc_results = await self.qdrant_searcher.search_documents(
                query=product_query,
                store_name=store_name,
                doc_type="product_document",
                limit=2,
                score_threshold=0.6
            )
            
            # Format results
            products_info = []
            if product_results:
                for product in product_results:
                    product_info = {
                        "product_id": product.get("product_id", ""),
                        "title": product.get("title", ""),
                        "vendor": product.get("vendor", ""),
                        "product_type": product.get("product_type", ""),
                        "price": product.get("price", ""),
                        "tags": product.get("tags", []),
                        "availability": product.get("available", True),
                    }
                    products_info.append(product_info)
            
            # Format documentation
            docs_text = []
            if doc_results:
                for doc in doc_results:
                    docs_text.append(doc.get("text", ""))
            
            return {
                "products": products_info,
                "additional_info": "\n\n".join(docs_text) if docs_text else "No additional product details available."
            }
            
        except Exception as e:
            logger.error(f"Error in get_product_information: {e}")
            return {
                "error": f"I encountered an error while retrieving product information: {str(e)}",
                "products": [],
                "additional_info": ""
            }
    
    @llm.ai_callable()
    async def get_order_status(
        self,
        order_id: Annotated[
            Optional[str], llm.TypeInfo(description="The order ID or order number")
        ] = None,
    ):
        """
        Get the status of a customer's order. If order_id is provided, it will look up that specific order.
        If not, it will attempt to find recent orders for the caller.
        """
        agent = AgentCallContext.get_current().agent
        await agent.say("Let me check that order status for you.", add_to_chat_ctx=True)
        
        try:
            if not self.shopify:
                self.shopify = ShopifyDataCollector(
                    shopify_access_token=shopify_access_token,
                    shopify_base_url=shopify_base_url
                )
            
            orders = []
            customer_id = None
            
            # Try direct order lookup if ID is provided
            if order_id:
                order = await self._get_order_by_id(order_id)
                if order:
                    orders = [order]
            
            # Fallback to customer lookup
            if not orders and caller_number:
                customer_id = await self.shopify.fetch_customer_id(str(caller_number))
                print("customer_id",customer_id)
                if customer_id:
                    orders = await self.shopify.get_customer_orders(customer_id)
            
            if not orders:
                error_msg = "I couldn't find any orders"
                if order_id:
                    error_msg += f" matching #{order_id}"
                if customer_id:
                    error_msg += " associated with your account"
                
                return {
                    "found": False,
                    "error": error_msg,
                    "orders": []
                }
            
            formatted_orders = []
            for order in orders[:3]:  # Limit to the 3 most recent orders
                formatted_order = {
                    "order_number": order.get("order_number", "N/A"),
                    "order_date": order.get("created_at", "N/A").split("T")[0] if order.get("created_at") else "N/A",
                    "total_price": order.get("total_price", "N/A"),
                    "payment_status": order.get("financial_status", "N/A"),
                    "fulfillment_status": order.get("fulfillment_status", "processing") or "processing",
                    "tracking_number": None,  # Add tracking number extraction logic if needed
                    "shipping_address": self._format_address(order.get("shipping_address", {})),
                    "items": [
                        {
                            "name": item.get("name", "Unknown item"),
                            "quantity": item.get("quantity", 1),
                            "price": item.get("price", "N/A")
                        }
                        for item in order.get("line_items", [])
                    ]
                }
                formatted_orders.append(formatted_order)
            
            return {
                "found": True,
                "orders": formatted_orders,
                "specific_order_id": order_id
            }
            
        except Exception as e:
            logger.error(f"Error in get_order_status: {e}")
            return {
                "found": False,
                "error": f"I encountered an error while retrieving order information: {str(e)}",
                "orders": []
            }
    
    @llm.ai_callable()
    async def update_order(
        self,
        order_id: Annotated[
            str, llm.TypeInfo(description="The order ID or order number to update")
        ],
        email: Annotated[
            Optional[str], llm.TypeInfo(description="New email address")
        ] = None,
        phone: Annotated[
            Optional[str], llm.TypeInfo(description="New phone number")
        ] = None,
        address1: Annotated[
            Optional[str], llm.TypeInfo(description="New street address line 1")
        ] = None,
        address2: Annotated[
            Optional[str], llm.TypeInfo(description="New street address line 2")
        ] = None,
        city: Annotated[
            Optional[str], llm.TypeInfo(description="New city")
        ] = None,
        last_name: Annotated[
            Optional[str], llm.TypeInfo(description="New last name")
        ] = None,
        province_code: Annotated[
            Optional[str], llm.TypeInfo(description="New province/state code")
        ] = None,
        country: Annotated[
            Optional[str], llm.TypeInfo(description="New country")
        ] = None,
        zip_code: Annotated[
            Optional[str], llm.TypeInfo(description="New ZIP/postal code")
        ] = None,
    ):
        """
        Update a customer's order information, such as shipping address, email, or phone number.
        """
        agent = AgentCallContext.get_current().agent
        await agent.say("I'm processing your order update request.", add_to_chat_ctx=True)
        
        try:
            if not self.shopify:
                self.shopify = ShopifyDataCollector(
                    shopify_access_token=shopify_access_token,
                    shopify_base_url=shopify_base_url
                )
            
            # Verify the order exists
            order = await self._get_order_by_id(order_id)
            if not order:
                return {
                    "success": False,
                    "error": f"I couldn't find order #{order_id}. Please verify the order number."
                }
            
            # Check what fields are being updated
            updated_fields = []
            if email:
                updated_fields.append("email")
            if phone:
                updated_fields.append("phone number")
            if any([address1, address2, city, last_name, province_code, country, zip_code]):
                updated_fields.append("shipping address")
            
            if not updated_fields:
                return {
                    "success": False,
                    "error": "No update information provided. Please specify what you'd like to update."
                }
            
            # Attempt to update the order
            result = await self.shopify.update_order(
                order_id=order_id,
                email=email,
                phone=phone,
                address1=address1,
                address2=address2,
                city=city,
                last_name=last_name,
                province_code=province_code,
                country=country,
                zip1=zip_code
            )
            
            if result:
                fields_str = ", ".join(updated_fields)
                return {
                    "success": True,
                    "order_id": order_id,
                    "updated_fields": updated_fields,
                    "message": f"Successfully updated {fields_str} for order #{order_id}."
                }
            else:
                return {
                    "success": False,
                    "error": f"Unable to update order #{order_id}. The order may be fulfilled, canceled, or there might be a system error."
                }
                
        except Exception as e:
            logger.error(f"Error in update_order: {e}")
            return {
                "success": False,
                "error": f"I encountered an error while updating your order: {str(e)}"
            }
    
    @llm.ai_callable()
    async def cancel_order(
        self,
        order_id: Annotated[
            str, llm.TypeInfo(description="The order ID or order number to cancel")
        ],
        reason: Annotated[
            Optional[str], llm.TypeInfo(description="Reason for cancellation")
        ] = "Customer requested cancellation",
    ):
        """
        Cancel a customer's order.
        """
        agent = AgentCallContext.get_current().agent
        await agent.say("I'm processing your cancellation request.", add_to_chat_ctx=True)
        
        try:
            if not self.shopify:
                self.shopify = ShopifyDataCollector(
                    shopify_access_token=shopify_access_token,
                    shopify_base_url=shopify_base_url
                )
            
            # Verify the order exists
            order = await self._get_order_by_id(order_id)
            if not order:
                return {
                    "success": False,
                    "error": f"I couldn't find order #{order_id}. Please verify the order number."
                }
            
            # Check if the order is already fulfilled
            if order.get("fulfillment_status") == "fulfilled":
                return {
                    "success": False,
                    "error": f"Order #{order_id} has already been fulfilled and cannot be canceled. Please contact customer support for assistance."
                }
            
            # Attempt to cancel the order
            result = await self.shopify.cancel_order(order_id, reason)
            
            if result:
                return {
                    "success": True,
                    "order_id": order_id,
                    "message": f"Successfully canceled order #{order_id}. You'll receive a confirmation email shortly."
                }
            else:
                return {
                    "success": False,
                    "error": f"Unable to cancel order #{order_id}. The order may already be fulfilled, shipped, or there might be a system error."
                }
                
        except Exception as e:
            logger.error(f"Error in cancel_order: {e}")
            return {
                "success": False,
                "error": f"I encountered an error while canceling your order: {str(e)}"
            }
    
    @llm.ai_callable()
    async def get_store_information(
        self,
        specific_info: Annotated[
            Optional[str], llm.TypeInfo(description="Specific store information to retrieve (hours, policies, etc.)")
        ] = None,
    ):
        """
        Get information about the store, such as contact details, business hours, policies, etc.
        """
        agent = AgentCallContext.get_current().agent
        await agent.say("Let me find that information for you.", add_to_chat_ctx=True)
        
        try:
            if not self.qdrant_searcher:
                self.qdrant_searcher = QdrantSearcher()
            
            # Prepare the query based on what specific information is requested
            query = specific_info if specific_info else "store information"
            
            # Get store information
            store_info = await self.qdrant_searcher.get_store_details(store_name)
            
            # Search for relevant store documents
            doc_results = await self.qdrant_searcher.search_documents(
                query=query,
                store_name=store_name,
                limit=3,
                score_threshold=0.6
            )
            
            # Combine information
            result = {
                "store_name": store_name,
                "general_info": store_details if store_details else "No general store information available."
            }
            
            if doc_results:
                relevant_docs = [doc.get("text", "") for doc in doc_results]
                result["relevant_info"] = "\n\n".join(relevant_docs)
            else:
                result["relevant_info"] = "No specific information found for your query."
            
            return result
            
        except Exception as e:
            logger.error(f"Error in get_store_information: {e}")
            return {
                "error": f"I encountered an error while retrieving store information: {str(e)}",
                "store_name": store_name,
                "general_info": store_details if store_details else "",
                "relevant_info": ""
            }
    
    async def _get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Helper to retrieve order by ID using Shopify API"""
        try:
            all_orders = await self.shopify.get_all_orders()
            return next((o for o in all_orders if str(o.get('id')) == order_id or
                        str(o.get('order_number')) == order_id), None)
        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return None
    
    def _format_address(self, address: Dict[str, Any]) -> str:
        """Format an address dictionary into a readable string"""
        if not address:
            return "No address information available"
        
        components = []
        if name := address.get('name'):
            components.append(name)
        if address1 := address.get('address1'):
            components.append(address1)
        if address2 := address.get('address2'):
            components.append(address2)
        
        city_state_zip = []
        if city := address.get('city'):
            city_state_zip.append(city)
        if province := address.get('province_code'):
            city_state_zip.append(province)
        if zip_code := address.get('zip'):
            city_state_zip.append(zip_code)
        
        if city_state_zip:
            components.append(", ".join(city_state_zip))
        
        if country := address.get('country'):
            components.append(country)
        
        return "\n".join(components) if components else "No address information available"
    
    @llm.ai_callable()
    async def transfer_to_agent(
        self,
        reason: Annotated[
            Optional[str], llm.TypeInfo(description="Reason for transferring to a human agent")
        ] = "Customer requested human assistance",
    ):
        """
        Transfer the call to a human agent.
        This function should be used when a customer explicitly requests to speak with a human,
        or when their query is too complex for the AI assistant to handle.
        """
        agent = AgentCallContext.get_current().agent
        await agent.say("I understand you'd like to speak with a human representative. I'll transfer your call now.", add_to_chat_ctx=True)
        
        try:
            # Determine the appropriate transfer number
            # This could be fetched from Redis or another configuration source
            transfer_number = os.getenv("TRANSFER_PHONE_NUMBER")
            if not transfer_number:
                # Fallback to a store-specific transfer number if available
                transfer_number = redis_client.hget(f"store:{called_number}", "transfer_number")
            
            if not transfer_number:
                return {
                    "success": False,
                    "error": "No transfer number configured for this store."
                }
                
            # Get the current call context
            call_ctx = AgentCallContext.get_current()
            participant = call_ctx.agent._participant
            participant_identity = participant.identity if participant else None
            # call_ctx
            
            if not participant_identity:
                return {
                    "success": False,
                    "error": "Unable to identify current participant for transfer."
                }
                
            # Initialize LiveKit API client
            livekit_url = os.getenv('LIVEKIT_URL')
            api_key = os.getenv('LIVEKIT_API_KEY')
            api_secret = os.getenv('LIVEKIT_API_SECRET')
            
            if not (livekit_url and api_key and api_secret):
                logger.error("Missing LiveKit API credentials for call transfer")
                return {
                    "success": False,
                    "error": "Missing required API credentials for call transfer."
                }
                
            livekit_api = api.LiveKitAPI(
                url=livekit_url,
                api_key=api_key,
                api_secret=api_secret
            )
            
            # Prepare transfer request
            
            transfer_request = TransferSIPParticipantRequest(
                participant_identity=participant_identity,
                room_name=self.room_name,
                transfer_to=transfer_number,
                play_dialtone=True
            )
            
            # Execute transfer
            logger.info(f"Transferring call for participant {participant_identity} to {transfer_number}")
            await livekit_api.sip.transfer_sip_participant(transfer_request)
            
            # Update conversation log
            # nonlocal escalation_requested
            # escalation_requested = True
            # conversation_log.append(f"SYSTEM: Call transferred to human agent. Reason: {reason}\n\n")
            
            return {
                "success": True,
                "transfer_to": transfer_number,
                "message": f"Successfully transferred call to human agent"
            }
                
        except Exception as e:
            logger.error(f"Error in transfer_to_agent: {e}")
            return {
                "success": False,
                "error": f"I encountered an error while transferring your call: {str(e)}"
            }

def prewarm_process(proc: JobProcess):
    """Preload components to speed up session start."""
    # Preload silero VAD in memory
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Preloaded Silero VAD")


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the Livekit agent."""
    global store_name, store_details, shopify_access_token, shopify_base_url, called_number, caller_number
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    
    # Initialize function context for Shopify operations
    shopify_fnc = ShopifyFunctions(ctx.room.name)
    
    # Initial system context
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant for an online Shopify Store. Your interface with users will be voice. "
            "You can manage orders, provide product information, and answer general store-related inquiries. "
            "Keep your responses clear, concise, and conversational. Avoid using punctuation that would be awkward "
            "in spoken language. When performing function calls, briefly let the user know that you're retrieving "
            "or processing their request."
        ),
    )
    
    # Create the agent
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata.get("vad", silero.VAD.load()),
        stt=deepgram.STT(),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(),
        fnc_ctx=shopify_fnc,
        chat_ctx=initial_ctx,
    )
    
    # Set up metrics collection
    usage_collector = metrics.UsageCollector()
    
    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        metrics.log_metrics(mtrcs)
        usage_collector.collect(mtrcs)
    
    # Set up chat handling
    chat = rtc.ChatManager(ctx.room)
    
    # Session tracking
    session_id = f"session_{datetime.now().timestamp()}"
    session_start_time = datetime.now()
    conversation_log = []
    user_id = 1  # Default or guest user ID
    store_id = 1  # Default or placeholder store ID
    detected_intent = None
    escalation_requested = False
    
    @agent.on("user_speech_committed")
    def on_user_speech_committed(msg: llm.ChatMessage):
        """Handle and log user speech."""
        nonlocal detected_intent, escalation_requested
        
        # Process text content
        content = msg.content
        if isinstance(content, list):
            content = "\n".join(
                "[image]" if isinstance(x, llm.ChatImage) else x for x in content
            )
        
        # Detect intent from user message
        try:
            # intent = intent_classifier.classify_intent(content, )
            # if intent:
            #     detected_intent = intent
            #     logger.info(f"Detected intent: {intent}")
            
            # Check for escalation request
            if "speak to human" in content.lower() or "talk to agent" in content.lower() or "agent please" in content.lower():
                escalation_requested = True
                logger.info("Escalation requested by user")
        except Exception as e:
            logger.error(f"Error processing user speech: {e}")
        
        # Log the user's message
        conversation_log.append(f"USER:\n{content}\n\n")
    
    @agent.on("agent_speech_committed")
    def on_agent_speech_committed(msg: llm.ChatMessage):
        """Handle and log agent speech."""
        conversation_log.append(f"AGENT:\n{msg.content}\n\n")
    
    async def save_conversation_to_db():
        """Save the conversation to the database when the session ends."""
        try:
            conversation_data = {
                'Conversation': ''.join(conversation_log),
                'User_ID': user_id,
                'Store_ID': store_id,
                'Session_ID': session_id,
                'Session_Time': session_start_time,
                'Duration_of_Call': (datetime.now() - session_start_time).seconds,
                # 'Call_Reason': detected_intent,
                'Escalation': escalation_requested,
                'Query_Type': detected_intent,
            }
            insert_conversation_to_db(conversation_data)
            
            # Log usage metrics
            summary = usage_collector.get_summary()
            logger.info(f"Session ended. Usage summary: {summary}")
        except Exception as e:
            logger.error(f"Error saving conversation: {e}")
    
    # Register the save function to be called when the session ends
    ctx.add_shutdown_callback(save_conversation_to_db)
    
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        loop = asyncio.get_running_loop()
        """Handle new participants joining the call."""
        global store_name, store_details, shopify_access_token, shopify_base_url, called_number, caller_number, customer_id
        
        logger.info(f"New participant joined: {participant.identity}")
        
        # Get the phone numbers
        called_number = participant.attributes.get('sip.trunkPhoneNumber')
        caller_number = participant.attributes.get('sip.phoneNumber')
        
        # Get store details from Redis
        store_name, store_details, shopify_access_token, shopify_base_url = get_store_from_redis(called_number)

        logger.info(f"Store Name: {store_name}, Store Details: {store_details}, Shopify Access Token: {shopify_access_token}, Shopify Base URL: {shopify_base_url}")
        
        logger.info(f"Called number: {called_number}, Store Name: {store_name}")
        logger.info(f"Caller number: {caller_number}")
        
        # Initialize ShopifyDataCollector with the store credentials
        shopify = ShopifyDataCollector(
            shopify_access_token=shopify_access_token, 
            shopify_base_url=f"https://{shopify_base_url}/admin/api/2025-01"
        )
    
        # Define a callback function to handle the result
        def handle_customer_id(task):
            try:
                customer_id = task.result()
                # Do something with customer_id
                print(f"Found customer ID: {customer_id}")
            except Exception as e:
                print(f"Error fetching customer ID: {e}")

        customer_id = loop.create_task(shopify.fetch_customer_id(caller_number))
        # customer_id = asyncio.get_event_loop().run_until_complete(shopify.fetch_customer_id(caller_number))
        logger.info(f"Customer ID: {customer_id}")

        
        # Update the function context with the initialized handlers
        shopify_fnc.shopify = shopify
        
        if store_name:
            # Update the system prompt with store information
            agent.chat_ctx.append(
                role="system",
                text=f"""You are a voice assistant for {store_name}. Your interface with users will be voice.
                    You can deal with customer's orders, product inquiries, and general customer support.
                    You should use short and concise responses, avoiding usage of unpronounceable punctuation.
                    Below given are the details of this particular store:
                    {store_details}
                    
                    When customers ask about products, use the get_product_information function.
                    When customers ask about orders, use the get_order_status function.
                    When customers ask to update orders, use the update_order function.
                    When customers ask to cancel orders, use the cancel_order function.
                    When customers ask about store policies or information, use the get_store_information function.
                    
                    Always be helpful and polite. If you cannot assist a customer with their request,
                    apologize and offer to connect them with a human representative.
                """,
            )
            
            # Start the agent
            agent.start(ctx.room, participant)
            
            # Welcome the user
            asyncio.create_task(agent.say(
                f"Hello, welcome to {store_name}. How can I help you today?", 
                allow_interruptions=True
            ))
        else:
            # Fallback if store information couldn't be retrieved
            agent.chat_ctx.append(
                role="system",
                text=(
                    "You are a voice assistant for an online store. You can help with product inquiries, "
                    "order status, and general customer support. "
                    "Please note that we're experiencing some technical difficulties retrieving the store information. "
                    "I'll still do my best to help you with your query."
                ),
            )
            
            # Start the agent
            agent.start(ctx.room, participant)
            
            # Welcome the user with a generic message
            asyncio.create_task(agent.say(
                "Hello, welcome to our online store. How can I help you today?", 
                allow_interruptions=True
            ))
            
            # Log the error
            logger.error(f"Failed to retrieve store info for phone number: {called_number}")

 # Clean up resources at the end of the session
    #await ctx.shutdown()
    #await agent.aclose()

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm_process,
        ),
    )
