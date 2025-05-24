import asyncio
import os
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import json
import re

# Load API keys
openai_api_key = os.getenv('OPENAI_API_KEY')

def clean_text(text):
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', '', text)

    # Remove Markdown headers (e.g., # Heading)
    text = re.sub(r'(^|\n)#+\s', '', text)
    
    # Remove Markdown links (e.g., [text](url))
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove Markdown images (e.g., ![alt](url))
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    
    # Remove Markdown emphasis (bold, italics, etc.)
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)  # **text** or __text__
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)     # *text* or _text_

    # Remove markdown links (e.g., [text](url))
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)

    # Remove URLs
    text = re.sub(r'http\S+|www\.\S+', '', text)

    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()

    return text

# Define function to generate embeddings and store them in a vector store
async def save_embeddings_to_vector_store(text_data, vectorstore):
    # Initialize OpenAI embedding model
    embeddings_model = OpenAIEmbeddings(openai_api_key=openai_api_key)

    # Generate embeddings for each extracted content
    embeddings = embeddings_model.embed_documents([text_data])

    # Add embedding to the vector store
    vectorstore.add_texts([text_data], embeddings)

async def main():
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Define extraction strategy with instructions
        strategy = LLMExtractionStrategy(
            provider='openai',
            api_token=openai_api_key,
            instruction="Extract only company related details like About Us and other relevant information. Remove all HTML tags."
        )

        # Sample URL
        url = "https://petroverusa.com/"

        # Run the crawler with the extraction strategy
        result = await crawler.arun(url=url, extraction_strategy=strategy)

        # Parse extracted content
        extracted = json.loads(result.extracted_content)

        # Initialize vector store (chroma in this case)
        embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        vector_store = Chroma(
            collection_name="example_collection",
            embedding_function=embeddings,
        )

        print("Cleaned content")
        for res in extracted:
            text_content = res['content']
            # print(f"Extracted content before cleaning: {text_content}")
            
            # Clean the extracted content
            cleaned_text = clean_text(text_content)
            print(cleaned_text)
            
            # Save cleaned content as embeddings to the vector store
            # await save_embeddings_to_vector_store(cleaned_text, vector_store)

        # Save vector store index
        # vectorstore.save_local("vector_store_index")

# Run the async main function
asyncio.run(main())
