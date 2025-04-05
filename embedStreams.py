import hashlib
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any
import time

# Environment configuration
def load_api_key() -> str:
    """Load OpenAI API key from .env.local"""
    load_dotenv('.env.local')
    api_key = os.getenv('oai')
    if not api_key:
        raise ValueError("API key not found in .env.local file")
    return api_key

# File operations
def read_streams(file_path: str = 'streams.json') -> List[Dict[str, Any]]:
    """Read streams from the json file"""
    with open(file_path, 'r') as file:
        return json.load(file)

def write_streams(streams: List[Dict[str, Any]], file_path: str = 'streams.json') -> None:
    """Write streams back to the json file"""
    with open(file_path, 'w') as file:
        json.dump(streams, file, indent=2)

# Embedding generation
def create_openai_client() -> OpenAI:
    """Create and return an OpenAI client"""
    api_key = load_api_key()
    return OpenAI(api_key=api_key)

def load_embedding_cache(cache_file: str = 'embeddingCache.json') -> Dict[str, List[float]]:
    """Load the embedding cache from file"""
    if not os.path.exists(cache_file):
        return {}
    with open(cache_file, 'r') as f:
        return json.load(f)

def save_embedding_cache(cache: Dict[str, List[float]], cache_file: str = 'embeddingCache.json') -> None:
    """Save the embedding cache to file"""
    with open(cache_file, 'w') as f:
        json.dump(cache, f, indent=2)

def get_text_hash(text: str) -> str:
    """Generate a stable hash for the input text"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def generate_embedding(client: OpenAI, text: str) -> List[float]:
    """Generate embedding for text using OpenAI API with caching"""
    # Load cache
    cache = load_embedding_cache()
    text_hash = get_text_hash(text)

    # Check cache
    if text_hash in cache:
        print(f"Using cached embedding for: {text[:25]}{"..." if len(text) > 25 else ""}")
        return cache[text_hash]

    # Generate new embedding
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format='float',
            dimensions=256
        )
        embedding = response.data[0].embedding

        # Update cache
        cache[text_hash] = embedding
        save_embedding_cache(cache)

        return embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

# Stream processing
def get_stream_text(stream: Dict[str, Any]) -> str:
    """Extract text to embed from a stream"""
    return f"{stream['name']}. {stream['description']}"

def process_stream(stream: Dict[str, Any], client: OpenAI) -> Dict[str, Any]:
    """Process a single stream to add embedding or return existing one"""
    if 'embedding' in stream and len(stream['embedding']) == 256:
        print(f"Stream {stream['name']} already has an embedding")
        return stream
    updated_stream = stream.copy()
    text = get_stream_text(stream)
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
        write_streams(updated_streams)
        
        print(f"Embedded {len(updated_streams)} streams successfully")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()