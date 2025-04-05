import hashlib
import os
import json
from openai import OpenAI
from typing import List, Dict, Any
import time

from utils import create_mongo_client, create_openai_client


# If this changes, delete all entries of the cache and db
DIMENSIONS = 1024

# File operations
def read_streams(file_path: str = 'streams.json') -> List[Dict[str, Any]]:
    """Read streams from the json file"""
    with open(file_path, 'r') as file:
        return json.load(file)

def load_embedding_cache(cache_file: str = 'embeddingCache.local.json') -> Dict[str, List[float]]:
    """Load the embedding cache from file"""
    if not os.path.exists(cache_file):
        return {}
    with open(cache_file, 'r') as f:
        return json.load(f)

def save_embedding_cache(cache: Dict[str, List[float]], cache_file: str = 'embeddingCache.local.json') -> None:
    """Save the embedding cache to file"""
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)

def generate_embedding(client: OpenAI, text: str) -> List[float]:
    """Generate embedding for text using OpenAI API with caching"""
    # Load cache
    cache = load_embedding_cache()
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()

    # Check cache
    if text_hash in cache:
        print(f"Using cached embedding for: {text[:25]}{"..." if len(text) > 25 else ""}")
        return cache[text_hash]

    # Generate new embedding
    try:
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=text,
            encoding_format='float',
            dimensions=DIMENSIONS,
        )
        embedding = response.data[0].embedding

        # Update cache
        cache[text_hash] = embedding
        save_embedding_cache(cache)

        return embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def process_stream(stream: Dict[str, Any], client: OpenAI) -> Dict[str, Any]:
    """Process a single stream to add embedding or return existing one"""
    if 'embedding' in stream and len(stream['embedding']) == DIMENSIONS:
        print(f"Stream {stream['name']} already has an embedding")
        return stream
    updated_stream = stream.copy()
    text = f"{stream['name']}. {stream['description']}"
    updated_stream['embedding'] = generate_embedding(client, text)
    return updated_stream

def process_all_streams(streams: List[Dict[str, Any]], client: OpenAI) -> List[Dict[str, Any]]:
    """Process all streams and add embeddings"""
    updated_streams = []
    total = len(streams)
    
    for i, stream in enumerate(streams):
        print(f"Processing stream {i+1}/{total}: {stream['name']}")
        updated_stream = process_stream(stream, client)
        updated_streams.append(updated_stream)
        # Add a small delay to avoid rate limiting
        if i < total - 1:
            time.sleep(0.1)
    
    return updated_streams

def upload_streams_to_mongo(streams: List[Dict[str, Any]]) -> None:
    """Upload streams to MongoDB"""
    mongo_client = create_mongo_client()
    collection = mongo_client["streams"]["streams"]
    collection.insert_many(streams)

    # Reset streams.json after upload
    with open('streams.json', 'w') as file:
        json.dump([], file, indent=2)

# Main function
def main():
    try:
        # Set up environment and client
        client = create_openai_client()
        
        # Read streams
        streams = read_streams()
        print(f"Found {len(streams)} streams to process")
        
        # Process streams
        updated_streams = process_all_streams(streams, client)
        
        # Save results
        upload_streams_to_mongo(updated_streams)
        
        print(f"Embedded {len(updated_streams)} streams successfully")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()