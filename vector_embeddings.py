import json
from bs4 import BeautifulSoup
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import Qdrant
from langchain_core.documents import Document
import os
from dotenv import load_dotenv


load_dotenv()

with open("voicebot-live-kit/json/data_all_products_combined.json", "r") as f:
    data = json.load(f)


def clean_html(html_content):
    '''
    Function to clean HTML content and extract text
    '''
    soup = BeautifulSoup(html_content, "html.parser")
    # Remove all <a> tags
    for a_tag in soup.find_all("a"):
        a_tag.extract()
    # Get text without any HTML tags
    clean_text = soup.get_text(separator=" ").strip()
    return clean_text


def extract_available_colors(html_content):
    '''
    Function to extract available colors from body_html
    '''
    soup = BeautifulSoup(html_content, "html.parser")
    available_colors = []
    color_section = soup.find('div', class_='Available')
    if color_section:
        for a_tag in color_section.find_next_siblings('div'):
            color = a_tag.get_text(strip=True)
            if color:
                available_colors.append(color)
    return available_colors


# Initialising the keys and the OpenAI Emebeddings model
QDRANT_URL = os.environ.get('QDRANT_URL', 'QDRANT_URL')
QDRANT_API_KEY = os.environ.get('QDRANT_API_KEY', 'QDRANT_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'OPENAI_API_KEY')
collection_name = "combined_store_products"
embedding_model = OpenAIEmbeddings(api_key=OPENAI_API_KEY)


store_name = "HPZ Pet Rover"
documents = []

for category_key, category_value in data["store_name"][0][store_name][0]["product_categories"].items():
    print(f"[ LOG ] - Making Documents for the Category: {category_key}")
    product_category = category_value["title"]
    for product in category_value["products"]:
        product_id = product["id"]
        product_title = product["title"]
        product_description_html = product["body_html"]
        product_description = clean_html(product_description_html)
        available_colors = extract_available_colors(product_description_html)
        
        metadata = {
            "store_name": store_name,
            "product_category": product_category,
            "id": product_id,
            "query_type": "product_description",
            "title": product_title,
            "product_type": product["product_type"],
            "created_at": product["created_at"],
            "updated_at": product["updated_at"],
            "fulfillment_service": product.get("fulfillment_service", ""),
            "grams": product.get("grams", 0),
            "requires_shipping": product.get("requires_shipping", False),
            "status": product.get("status", ""),
            "weight": product.get("weight", 0),
            "weight_unit": product.get("weight_unit", ""),
            "available_colors": available_colors
        }
        # print(f"[ LOG ] - Metadata: {metadata}")
        # break
        
        # Create a document with the cleaned product description and metadata
        document = Document(
            page_content=product_description,
            metadata=metadata
        )
        documents.append(document)
if "additional_data_source" in data["store_name"][0][store_name][0]:
    for data_source_key, data_source_value in data["store_name"][0][store_name][0]["additional_data_source"].items():
        print(f"[ LOG ] - Making Documents for the Data Source: {data_source_key}")
        print(f"[ LOG ] - Data Source Type: {data_source_value['type']}")
        for faq in data_source_value["faqs"]:
            question = faq["question"]
            answer = faq["answer"]
            metadata = {
                "store_name": store_name,
                "query_type": data_source_value["type"],
                "question": question
            }
            # print("----------------")
            # print(f"[ LOG ] - Metadata: {metadata}")
            # print("----------------")
            document = Document(
                page_content=answer,
                metadata=metadata
            )
            documents.append(document)
# Initialize Qdrant client and upload documents

# '''
# curl \
#     -X GET 'https://ee6e7672-cadc-4b87-b60b-3a8c4e065b94.us-east4-0.gcp.cloud.qdrant.io:6333' \
#     --header 'api-key: d1UxopIl7qP9qBbuvmyIA2sU-9Y6LsIi1vGOWHGgYvq7PiwKWk9wzQ'
# '''

doc_store = Qdrant.from_documents(
    documents=documents,
    embedding=embedding_model,
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    collection_name=collection_name,
    prefer_grpc=True,
)

print("Embeddings successfully uploaded to Qdrant.")