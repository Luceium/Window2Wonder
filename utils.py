import os
from pymongo import MongoClient
from openai import OpenAI
from dotenv import load_dotenv

def create_openai_client() -> OpenAI:
    """Create and return an OpenAI client"""
    load_dotenv('.env.local')
    api_key = os.getenv('oai')

    if not api_key:
        raise ValueError("API key not found in .env.local file")
    
    return OpenAI(api_key=api_key)

def create_mongo_client() -> MongoClient:
    """Create and return a MongoDB client"""
    load_dotenv('.env.local')
    uri = os.getenv('mongo')

    if not uri or (uri.startswith("mongodb://") is False and uri.startswith("mongodb+srv://") is False):
        raise ValueError("MongoDB URI not found in .env.local file")
    
    return MongoClient(uri)